"""Draft model-independent interaction protocol; no model/network client.
Only observation() output may cross the actor boundary. Keep the controller,
oracle, config and paired-task metadata out of the actor filesystem.
"""
from copy import deepcopy


def select_history(records, query, policy, embed=None, top_k=2):
    if policy == 'current_session':
        return []
    if policy != 'history_retrieval' or embed is None:
        raise ValueError('history_retrieval requires an explicitly supplied embed function')
    if not records:
        return []
    vectors = embed([query] + [r['text'] for r in records])
    if len(vectors) != len(records) + 1:
        raise ValueError('Embedding count mismatch')
    def cosine(a, b):
        if len(a) != len(b):
            raise ValueError('Embedding dimension mismatch')
        norm = sum(x*x for x in a)**.5 * sum(x*x for x in b)**.5
        return sum(x*y for x, y in zip(a, b))/norm if norm else 0.0
    # Stable deterministic ties; the actor receives selected records chronologically.
    scored = sorted(enumerate(records), key=lambda x: (-cosine(vectors[0], vectors[x[0]+1]), x[0]))
    return sorted([deepcopy(r) for _, r in scored[:top_k]], key=lambda r: r['timestamp'])


def local_dense_embedder(path):
    """For future authorized runs only. Local weights only; never downloads."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(path, device='cpu', local_files_only=True)
    return lambda texts: model.encode(texts, normalize_embeddings=True).tolist()


class EpisodeController:
    """Three checkpoints: omission, explicit revision, new-session omission.
    Scripted feedback is deliberately separate from native LLM user simulators.
    The bounded calibration driver is provided separately in run_local.py.
    """
    def __init__(self, public, oracle, policy, embed=None, top_k=2):
        if public['episode_id'] != oracle['episode_id']:
            raise ValueError('Episode/oracle mismatch')
        self.public, self.oracle = deepcopy(public), deepcopy(oracle)
        self.policy, self.embed, self.top_k = policy, embed, top_k
        self.history = deepcopy(public['history'])
        self.phase, self.asked, self.closed = 0, 0, False
        self.clock = max([999] + [r["timestamp"] for r in self.history])
        self.session = [self._message('u0', public['initial_request'])]
        self.evidence = set(oracle['initial_evidence_ids'])
        self.records = []
        self.last_observation = None

    def _tick(self):
        self.clock += 1
        return self.clock

    def _message(self, mid, text):
        return {'id': mid, 'role': 'user', 'text': text, 'timestamp': self._tick()}

    def observation(self):
        if self.closed:
            raise RuntimeError('Episode finished')
        query = self.public['scenario'] + ' ' + self.session[-1]['text']
        selected = select_history(self.history, query, self.policy, self.embed, self.top_k)
        # Never reveal arm, pair ID, target, correction script or future messages.
        self.last_observation = {'scenario': self.public['scenario'], 'slot': self.public['slot'],
            'candidates': deepcopy(self.public['candidates']), 'history': selected,
            'messages': deepcopy(self.session), 'clarifications_remaining': 1-self.asked}
        return deepcopy(self.last_observation)

    def respond(self, response):
        if self.closed or self.last_observation is None:
            raise RuntimeError('Call observation() before each response')
        if set(response) != {'kind', 'option_id', 'question_slot', 'claims'}:
            raise ValueError('Invalid response fields')
        kind = response['kind']
        if kind not in {'ask', 'commit', 'abstain'} or not isinstance(response['claims'], list):
            raise ValueError('Invalid response')
        allowed = {x['option_id'] for x in self.public['candidates']}
        if kind == 'commit' and (response['option_id'] not in allowed or response['question_slot'] is not None):
            raise ValueError('Invalid commit')
        if kind != 'commit' and response['option_id'] is not None:
            raise ValueError('Only commit may choose an option')
        if kind == 'abstain' and response['question_slot'] is not None:
            raise ValueError('Abstain cannot include a question')
        if kind == 'ask' and (self.asked or not isinstance(response['question_slot'], str)):
            raise ValueError('Question budget exhausted or question_slot missing')
        visible = {x['id'] for x in self.last_observation['history'] + self.last_observation['messages']}
        evidence_visible = self.evidence & visible
        target = self.oracle['phase_targets'][self.phase]
        unsupported = 0
        for claim in response['claims']:
            if set(claim) != {'slot', 'value', 'evidence_ids'} or not isinstance(claim['evidence_ids'], list):
                raise ValueError('Invalid claim')
            supported = (claim['slot'] == self.public['slot'] and claim['value'] == target
                         and bool(set(claim['evidence_ids']) & evidence_visible)
                         and set(claim['evidence_ids']) <= visible)
            unsupported += not supported
        record = {'phase': self.phase, 'response_index': self.asked, 'kind': kind,
            'question_count': int(kind == 'ask'),
            'unnecessary_question': int(kind == 'ask' and bool(evidence_visible)),
            'irrelevant_question': int(kind == 'ask' and response['question_slot'] != self.public['slot']),
            'claim_count': len(response['claims']), 'unsupported_claim_count': unsupported,
            'first_response_commit': int(kind == 'commit' and self.asked == 0),
            'committed': int(kind == 'commit'),
            'correct_action': int(kind == 'commit' and response['option_id'] == self.oracle['phase_options'][self.phase]),
            'clarification_required_given_visible_evidence': not bool(evidence_visible)}
        # Keep evaluated action records controller-side; never feed scores back to actor.
        self.records.append(record)
        self.session.append({'id': f'a{self.phase}_{self.asked}', 'role': 'assistant',
            'text': str(response), 'timestamp': self._tick()})
        self.last_observation = None
        if kind == 'ask':
            self.asked = 1
            mid = f'q{self.phase}'
            if response['question_slot'] == self.public['slot']:
                text = f'这次请按{target}处理。'
                self.evidence.add(mid)
            else:
                text = '与这次选择有关的其他条件已经给出；请只确认你缺少的偏好。'
            self.session.append(self._message(mid, text))
            return {'checkpoint_finished': False, 'episode_finished': False}
        self.phase += 1
        self.asked = 0
        if self.phase == 1:
            self.session.append(self._message('correction', self.oracle['correction_message']))
            self.evidence = {'correction'}
        elif self.phase == 2:
            # Prior user messages only. Do not treat assistant guesses as user preferences.
            for i, msg in enumerate(self.session):
                if msg['role'] == 'user':
                    self.history.append(deepcopy(msg))
            self.session = [self._message('u2', self.oracle['followup_request'])]
            self.evidence = {'correction'}
        else:
            self.closed = True
        return {'checkpoint_finished': True, 'episode_finished': self.closed}


def summarize_episode(records):
    """Counts retain their denominators. This is not a native benchmark score."""
    out = {}
    for phase in range(3):
        rows = [r for r in records if r['phase'] == phase]
        terminal = [r for r in rows if r['kind'] in {'commit','abstain'}]
        if len(terminal) != 1:
            raise ValueError('Incomplete or invalid checkpoint; do not silently exclude it')
        out[str(phase)] = {'correct_action': terminal[0]['correct_action'],
            'committed': terminal[0]['committed'],
            'first_response_commit': rows[0]['first_response_commit'],
            'question_count': sum(r['question_count'] for r in rows),
            'unnecessary_questions': sum(r['unnecessary_question'] for r in rows),
            'irrelevant_questions': sum(r['irrelevant_question'] for r in rows),
            'claim_count': sum(r['claim_count'] for r in rows),
            'unsupported_claim_count': sum(r['unsupported_claim_count'] for r in rows)}
    return out
