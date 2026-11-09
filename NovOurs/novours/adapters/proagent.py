from novours.inventory import inventory
from novours.core import dump


def run(config,out,journal):
    entries=[r for r in inventory()['entries'] if r['source']=='proagent']
    dump(out/'inclusion.json',entries)
    return {'status':'skipped','included':0,'skipped':len(entries),'reason':'Current source release lacks original evaluator/scoring targets and images. No synthetic goals or substitute scores.'}


def evaluate(config,out,journal): return run(config,out,journal)
