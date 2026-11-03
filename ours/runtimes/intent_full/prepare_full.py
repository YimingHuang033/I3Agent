from pathlib import Path
import json,hashlib,shutil,sys
from types import SimpleNamespace
P=Path('/home/tim/Proj/I3Agent');R=P/'intent_full_runtime';C=R/'campaigns/full-20261103-v1';OLD=P/'intent_diagnostics_runtime/campaigns/discussion-20261102-v1'
sys.path.insert(0,str(R));from run_local import fingerprint
projects=[P/n for n in ['pi_bench_ours1','lifesim_ours1','mempabench_ours1','proagentbench_ours1']]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
records=[];total=0
for p in projects:
 subsets=load(p/'ours1/data/private/subsets.json');assert set(subsets['discussion'])<=set(subsets['full']);total+=len(subsets['full'])
 cfg=load(p/'ours1/configs/experiment.json');assert cfg['training_enabled'] is False and cfg['full_execution_enabled']
assert total==10560
for model,name in [('qwen','Qwen3-8B'),('gptoss','gpt-oss-20b')]:
 args=SimpleNamespace(model=name,model_kind=model,subset='full',max_tokens=768,workers=8)
 fresh=fingerprint(projects,args);old=load(OLD/model/'manifest.json')
 assert all(old[k]==fresh[k] for k in ['model','model_kind','max_tokens','workers','temperature','seed'])
 for path,h in old['files'].items():
  src=Path(path);assert sha(src)==h,src
  target=R/src.name if src.parent.name=='intent_diagnostics_runtime' else src
  assert fresh['files'][str(target)]==h,target
 dst=C/model;out=dst/'episodes';out.mkdir(parents=True,exist_ok=True)
 assert not (dst/'manifest.json').exists(),'Refusing to reinitialize campaign'
 cases={p.name:set(load(p/'ours1/data/private/subsets.json')['discussion']) for p in projects}
 paths=list((OLD/model/'episodes').glob('*.json'));assert len(paths)==96
 for src in paths:
  row=load(src);assert row['model']==name and row['episode_id'] in cases[row['benchmark']] and row['baseline'] in ['full_history','correction_priority']
  assert set(row['checkpoint_scores'])=={'0','1','2'}
  dest=out/src.name;shutil.copyfile(src,dest);assert sha(src)==sha(dest)
  records.append({'source':str(src),'destination':str(dest),'sha256':sha(src),'status':row['status']})
 (dst/'manifest.json').write_text(json.dumps(fresh,indent=2))
files=list(R.glob('*.py'))+[Path(p) for p in fresh['files']]
(C/'scheduled-inputs.json').write_text(json.dumps({'sha256':{str(f):sha(f) for f in files},'task_cases':total,'total_episodes':42240,'reused':192,'new_calls_episodes':42048,'subset':'full','training_enabled':False},indent=2))
(C/'reuse-manifest.json').write_text(json.dumps(records,indent=2))
print('Verified and copied 192 episodes (including all original errors), 42048 remaining; 10560 tasks full coverage.')
