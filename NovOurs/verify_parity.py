"""Replay native LifeSim metric CLI on cached judge outputs; no model calls."""
import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from novours.core import SOURCES,dump,digest
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args()
out=a.run.resolve()
subprocess.run([sys.executable,str(SOURCES/'lifesim/src/evaluation/metric.py'),'--results_root',str(out/'eval_outputs'),'--models','run','--evaluators','judge','--output_root',str(out/'parity_native_cli')],check=True,env={**os.environ,'PYTHONPATH':str(SOURCES/'lifesim/src')})
original=json.loads((out/'parity_native_cli/run/scores.json').read_text())
adapted=json.loads((out/'scores.json').read_text())
result={'same_native_trajectory':True,'same_cached_judge_outputs':True,'native_cli_metrics':original,'adapter_metrics':adapted,'equal':original==adapted,'scope':'Aggregation parity only. Reuses cached judge responses to avoid stochastic judge differences; not a proof of every transport or tool trace field.'}
dump(out/'parity_native_cli.json',result)
if not result['equal']:raise SystemExit('Native metric parity failed')
print('PASS: original CLI and adapter scores are identical')
