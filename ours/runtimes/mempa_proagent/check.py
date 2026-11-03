"""Verify source-derived pairing, hidden targets and deterministic controller trajectories."""
from pathlib import Path
import json,hashlib
from protocol import EpisodeController,summarize_episode
ROOT=Path(__file__).resolve().parent.parent
out={}
for name in ['mempabench_ours1','proagentbench_ours1']:
 root=ROOT/name;data=root/'ours1/data';public={r['episode_id']:r for r in map(json.loads,(data/'public/episodes.jsonl').read_text().splitlines())};gold={r['episode_id']:r for r in map(json.loads,(data/'private/oracle.jsonl').read_text().splitlines())};pairs=json.loads((data/'private/pairs.json').read_text());assert public.keys()==gold.keys()
 for pair in pairs:
  if pair['kind']=='ambiguity_twins':
   aa,bb=[dict(public[i]) for i in pair['episode_ids']];aa.pop('episode_id');bb.pop('episode_id');assert aa==bb
 for cid,pub in public.items():
  g=gold[cid];c=EpisodeController(pub,g,'current_session')
  for phase in range(3):
   obs=c.observation();assert obs['history']==[] and not {'target','source','condition','episode_id'}&obs.keys()
   c.respond({'kind':'ask','option_id':None,'question_slot':pub['slot'],'claims':[]});obs=c.observation();assert obs['clarifications_remaining']==0
   c.respond({'kind':'commit','option_id':g['phase_options'][phase],'question_slot':None,'claims':[]})
  assert c.closed and all(x['correct_action'] for x in summarize_episode(c.records).values())
 manifest=json.loads((root/'SOURCE_SNAPSHOT.json').read_text())
 for x in manifest['files']:
  assert hashlib.sha256((root/x['path']).read_bytes()).hexdigest()==x['sha256']
  assert hashlib.sha256((Path(manifest['source'])/x['path']).read_bytes()).hexdigest()==x['sha256']
 out[name]={'episodes':len(public),'pairs':len(pairs),'equivalent_U_twins':True,'three_phase_gold_trajectory':'passed','source_hashes':'unchanged'}
(ROOT/'ours2_runtime/check-report.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
