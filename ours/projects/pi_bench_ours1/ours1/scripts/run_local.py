"""Compatibility entrypoint; shared implementation lives in ours1_runtime."""
from pathlib import Path
import runpy,sys
shared=Path(__file__).resolve().parents[3]/'ours1_runtime'
sys.path.insert(0,str(shared))
if __name__=='__main__':runpy.run_path(str(shared/'run_local.py'),run_name='__main__')
