"""Offline checks: all dataset trajectories, resume integrity, immutable sources."""
from pathlib import Path
import hashlib,json,tempfile,sys
from types import SimpleNamespace
from protocol import EpisodeController,summarize_episode
from run_local import atomic_json,prior_results,case_key,fingerprint,select_cases
ROOT=Path(__file__).resolve().parent.parent
report={}
for name in ['pi_bench_ours1','lifesim_ours1']:
 root=ROOT/name/'ours1';cases=select_cases(root,'full');assert len(cases)==2304
 assert len({c[0]['episode_id'] for c in cases})==2304
 for public,gold in cases:
  c=EpisodeController(public,gold,'current_session')
  for phase in range(3):
   obs=c.observation();assert not obs['history'] and not {'target','condition','episode_id'}&set(obs)
   before=(c.phase,len(c.records),len(c.session))
   try:c.respond(dict(kind='commit',option_id=None,question_slot=None,claims=[]))
   except ValueError:pass
   else:raise AssertionError('Invalid commit accepted')
   assert before==(c.phase,len(c.records),len(c.session))
   c.respond(dict(kind='ask',option_id=None,question_slot=public['slot'],claims=[]))
   obs=c.observation();ts=[m['timestamp'] for m in obs['messages']];assert ts==sorted(set(ts))
   c.respond(dict(kind='commit',option_id=gold['phase_options'][phase],question_slot=None,claims=[]))
  assert c.closed and all(x['correct_action']==1 for x in summarize_episode(c.records).values())
 with tempfile.TemporaryDirectory() as d:
  out=Path(d);job=(root,cases[0],'current_session')
  row=dict(episode_id=cases[0][0]['episode_id'],baseline='current_session',model='test',checkpoint_scores={str(i):{} for i in range(3)})
  atomic_json(out/(case_key(*job)+'.json'),row)
  done,todo=prior_results([job],out,'test');assert len(done)==1 and not todo
  try:prior_results([job],out,'other-model')
  except ValueError:pass
  else:raise AssertionError('Resume accepted wrong model')
  assert not list(out.glob('*.tmp'))
 manifest=json.loads((ROOT/name/'SOURCE_SNAPSHOT.json').read_text())
 for entry in manifest['files']:
  for p in [Path(manifest['source'])/entry['source_relative_path'],ROOT/name/entry['snapshot_relative_path']]:
   assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],str(p)
 report[name]={'cases':len(cases),'source_files':len(manifest['files']),'source_unchanged':True,'resume_identity_and_atomic_save':'passed','three_phase_protocol':'passed'}
print(json.dumps(report,indent=2))
(ROOT/'ours1_runtime/check-report.json').write_text(json.dumps(report,indent=2)+'\n')
