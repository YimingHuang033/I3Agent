"""Preserve pre-migration path spellings when resuming a frozen remote campaign."""
import argparse,importlib.util,json,os,sys,types
from pathlib import Path
ROOT=Path('/home/tim/Proj/I3Agent')
RUNTIMES=['ours1_runtime','ours2_runtime','intent_diagnostics_runtime','intent_full_runtime']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('runtime',choices=RUNTIMES);p.add_argument('--inspect',action='store_true')
 a,args=p.parse_known_args();legacy=ROOT/a.runtime
 spec=importlib.util.spec_from_file_location('legacy_monitor',legacy/'monitor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 canonical=module.ROOT
 if hasattr(module,'CAMPAIGN'):module.CAMPAIGN=legacy/module.CAMPAIGN.relative_to(canonical)
 module.ROOT=legacy
 if hasattr(module,'PROJECT'):module.PROJECT=ROOT
 if a.inspect:
  print(json.dumps({'ROOT':str(module.ROOT),'PROJECT':str(getattr(module,'PROJECT',ROOT)),'CAMPAIGN':str(getattr(module,'CAMPAIGN','from CLI'))}));return
 wrapper=str(Path(__file__).resolve());execv=os.execv
 def restart(executable,argv):
  execv(executable,[executable,wrapper,a.runtime,*argv[2:]])
 attrs=dict(vars(os));attrs['execv']=restart;module.os=types.SimpleNamespace(**attrs)
 sys.argv=[str(legacy/'monitor.py'),*args];module.main()
if __name__=='__main__':main()
