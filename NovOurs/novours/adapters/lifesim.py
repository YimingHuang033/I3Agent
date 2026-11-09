from __future__ import annotations
import json
import sys
from pathlib import Path
from novours.core import ROOT, SOURCES, Model, dump, digest
from novours.agents import Agent


def load_native():
    root = SOURCES / 'lifesim'
    sys.path.insert(0,str(root/'src'))
    return root


class AssistantBridge:
    """Replaces the assistant only. User profile/hidden event never reach Agent."""
    def __init__(self, agent, model, dimensions):
        self.agent, self.model, self.dimensions = agent, model, dimensions
        self.index = 0
        self.messages = []
        self.profile_dimensions = []

    def _build_user_profile(self, profile):
        # The native preference prediction task discloses dimension names, not values.
        self.profile_dimensions = list(profile.preferences_value)

    def reinit(self):
        self.messages = []

    def _build_system_prompt(self,event):
        self.index += 1
        public = {'dialogue_scene':event['dialogue_scene'],'conv_history':event.get('conv_history',[]),'user_can_correct':True}
        self.agent.begin(f'event-{self.index}',public)

    def respond(self,input,event,**kwargs):
        action = self.agent.act(input)
        self.messages += [{'role':'user','content':input},{'role':'assistant','content':action['text']}]
        # Native IR requires an explicit prediction; this is optional source diagnostic,
        # not an architecture requirement for every harness.
        intent = action.get('diagnostics',{}).get('intent','')
        return intent,action['text']

    def summarize(self,event,dimensions,**kwargs):
        from agents.prompts import ASSISTANT_PROFILE_SUMMARY_PROMPT
        from utils.utils import parse_json_dict_response, format_preferences
        by_name = {x['dimension']:x for x in self.dimensions}
        desc = ''
        for i,d in enumerate(dimensions):
            t = by_name[d]['template']
            desc += f'Dimension {i+1}: {d}\nValue "high" means "{t["high"]}" Value "middle" means "{t["middle"]}" Value "low" means "{t["low"]}"\n'
        prompt = ASSISTANT_PROFILE_SUMMARY_PROMPT.format(profile='',dialogue_scene=event['dialogue_scene'],conversation_context='\n'.join(m['role']+': '+m['content'] for m in self.messages),dimensions=desc)
        result = parse_json_dict_response(self.model.chat([{'role':'user','content':prompt}]),[])
        # Native format_preferences uses only dimension keys in its second arg.
        return format_preferences(result,{d:None for d in dimensions})

    def save(self,path): self.agent.end(path)


def run(config,out,journal):
    root = load_native()
    from agents.user_agent import UserAgent
    from agents.assistant_agent import AssistantAgent
    from engine.event_engine import OfflineLifeEventEngine
    from profiles.profile_generator import UserProfileGenerator
    from simulation.conversation_simulator import ConversationSimulator
    setting = config.get('setting','single_session')
    rows = [json.loads(x) for x in (root/'data'/setting/'events.jsonl').read_text().splitlines()]
    row = next((x for x in rows if x['id']==config.get('sequence_id')),None) if config.get('sequence_id') else rows[config.get('sequence_index',0)]
    n=config.get('events',1)
    if row is None:raise ValueError('unknown LifeSim sequence_id')
    if not 1<=n<=len(row['events']):raise ValueError(f"Requested {n} events but original sequence contains {len(row['events'])}; no synthetic extension is permitted")
    dump(out/'selection.json',{'sequence_id':row['id'],'setting':setting,'event_count':n,'sequence_sha256':digest(row),'rounds':config.get('rounds',2)})
    dims = json.loads((root/'data/language_templates.json').read_text())
    user_model = Model(config['user'],journal,'user')
    actor = Model(config['actor'],journal,'actor')
    embedding = Path(config['embedding_path'])
    if not embedding.is_absolute(): embedding = ROOT/embedding
    retrieval = dict(model_name=str(embedding),max_length=512,embedding_dim=1024,persist_directory=str(out/'chroma'),device='cpu',logger_silent=True,collection_name='novours_user')
    user = UserAgent(user_model,retrieval,alpha=0.5,logger_silent=True)
    if config['agent'].get('method') == 'native':
        assistant = AssistantAgent(actor,dims,logger_silent=True,retriever_config={**retrieval,'collection_name':'novours_assistant'})
    else:
        assistant = AssistantBridge(Agent(config['agent'],actor,journal),actor,dims)
    sim = ConversationSimulator(UserProfileGenerator(str(root/'data'/setting/'users.jsonl'),random_state=1),OfflineLifeEventEngine(str(root/'data'/setting/'events.jsonl')),user,assistant,logger_silent=True)
    sim.init_env(row['id'])
    # Deliberately do not use run_simulation's broad except-and-continue: a failed
    # episode is a failed run, not an apparently complete subset.
    for i in range(n):
        episode,_ = sim.run_episode(event_index=i+1,n_rounds=config.get('rounds',2),user_config={'use_emotion_chain':True,'use_dynamic_memory':True},assistant_config={'use_profile_memory':config['agent'].get('method')=='native','use_key_info_memory':False})
        dump(out/'logs'/'run'/'logs_0'/'sim_log.json',{'event_sequence_info':sim.life_event_engine.get_current_sequence_info(),'dialogue_log':sim.dialogue_log})
        journal.add('episode_complete',index=i,dialogue_turns=len(episode['dialogue']))
        sim.reset()
    dump(out/'selection.json',{'sequence_id':row['id'],'setting':setting,'event_count':n,'sequence_sha256':digest(row),'rounds':config.get('rounds',2)})
    assistant.save(str(out/'agent_state.json'))
    if isinstance(assistant,AssistantBridge): assistant.agent.close()
    return evaluate(config,out,journal)


def evaluate(config,out,journal):
    root = load_native()
    sys.path.insert(0,str(root/'src/evaluation'))
    import eval as native_eval
    import metric as native_metric
    before = native_eval.get_eval_dataset('run',str(out/'logs'))
    # Identity conversion: same native trajectory, JSON round-trip only. Check all
    # evaluator input structures, and aggregate the same cached judge outputs.
    after = json.loads(json.dumps(before))
    assert list(before)==after
    conv = before[2]
    judge = Model(config['judge'],journal,'judge')
    eval_dir = out/'eval_outputs'/'judge'/'run'
    eval_dir.mkdir(parents=True,exist_ok=True)
    for name,(fn,filename) in native_eval.METRIC_RUNNERS.items():
        path = eval_dir/filename
        if path.exists(): continue
        results = fn(conv,lambda:judge,max_workers=1)
        if any(not r.get('output') for r in results):
            raise RuntimeError(f'Native judge failed: {name}')
        native_eval.write_jsonl_data(results,str(path))
    scores = {}
    for fn in [native_metric.compute_ir_ic,native_metric.compute_nat,native_metric.compute_coh,native_metric.compute_pa,native_metric.compute_ea,native_metric.compute_rr]:
        scores.update(fn(str(out/'eval_outputs'),'run',['judge']))
    dump(out/'scores.json',scores)
    dump(out/'parity.json',{'native_input_sha256':digest(before),'adapter_input_sha256':digest(after),'equal':True,'method':'identity native log; cached original judge responses; original metric functions','scores':scores})
    return scores
