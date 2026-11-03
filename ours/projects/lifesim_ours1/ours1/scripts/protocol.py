"""Compatibility import for the shared, frozen episode protocol."""
from pathlib import Path
import runpy
shared=Path(__file__).resolve().parents[3]/'ours1_runtime/protocol.py'
globals().update({k:v for k,v in runpy.run_path(str(shared)).items() if not k.startswith('__')})
