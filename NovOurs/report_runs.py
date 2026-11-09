"""Render auditable smoke records, not a benchmark leaderboard."""
import json
from collections import Counter
from pathlib import Path
from novours.core import ROOT,dump
base=ROOT/'NovOurs';rows=[]
for manifest in sorted((base/'.local').glob('**/manifest.json')):
    if '/native/' in str(manifest):continue
    out=manifest.parent
    try:
        m=json.loads(manifest.read_text());status=json.loads((out/'status.json').read_text())
        if 'config' not in m:continue
    except (OSError,json.JSONDecodeError):continue
    calls=Counter();tokens=Counter();seconds=Counter();actions=Counter();diagnostics=0
    for trace in [out/'trace.jsonl',out/'agent_trace.jsonl']:
        if not trace.exists():continue
        for line in trace.read_text().splitlines():
            try:e=json.loads(line)
            except json.JSONDecodeError:continue
            if e['kind']=='model_call':
                role=e['role'];calls[role]+=1;tokens[role]+=e['response'].get('usage',{}).get('total_tokens',0);seconds[role]+=e.get('elapsed',0)
            if e['kind']=='agent_action':
                actions[e['action']['type']]+=1
                diagnostics+=bool(e['action'].get('diagnostics',{}).get('intent'))
    result=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
    metrics=result.get('native_metrics')
    if m['config']['source']=='pi' and metrics:
        metrics={k:metrics.get(k) for k in ['tasks_built','checklist_evaluated_tasks','proactiveness_evaluated_tasks','overall_average_score','overall_proactiveness_average_score']}
    rows.append({'run':str(out.relative_to(base)), 'source':m['config']['source'],'method':m['config']['agent']['method'],'status':status,'native_metrics':metrics,'calls':dict(calls),'tokens':dict(tokens),'request_seconds':{k:round(v,2) for k,v in seconds.items()},'wall_seconds':round(result['completed']-m['started'],2) if result.get('completed') else None,'actions':dict(actions),'intent_diagnostics':diagnostics,'source_versions':m.get('source_versions'), 'config_sha256':m.get('config_sha256'),'pi_call_accounting':'actor only for early smoke before LoggedClient; consult native logs for user/judge' if m['config']['source']=='pi' else None})
    rows[-1]['models']={role:m['config'][role]['model'] for role in ['actor','user','judge'] if role in m['config']}
    rows[-1]['code_hashes']=m.get('code_hashes')
    if out.name=='mempa-native-v4':rows[-1]['validation_warning']='Excluded: original CLI exited 0 despite MCP initialization failure; use v7'
    if out.name=='lifesim-stitch-official-v5':rows[-1]['validation_warning']='Excluded: upstream turns.jsonl lookup missed its expected parent layout and candidate IDs covered only the current turn; fixed in v6'
    rows[-1]['eligible_for_smoke_claims']=status['status']=='complete' and 'validation_warning' not in rows[-1]
dump(base/'docs/run-records.json',rows)
lines=['# 实际试跑记录','', '本文件由 `report_runs.py` 从 BBQCard2 原始运行产物生成。失败尝试一并保留。每行是 smoke，不构成统计比较；不同调试版本与预算不能直接作方法消融。token 是接口返回 usage；请求耗时相加不等于并发墙钟耗时。Pi 早期日志仅完整统计 actor 调用。','', '| 运行 | 方法 | 状态 | 墙钟秒 | 已记录模型调用 |', '|---|---|---|---:|---:|']
for r in rows:lines.append(f"| `{r['run']}` | {r['method']} | {r['status']['status']} | {r['wall_seconds']} | {sum(r['calls'].values())} |")
lines+=['','逐项原指标、后端调用量、token、动作计数、来源提交与配置散列见 `run-records.json`。原始对话与 native artifacts 在对应 `.local` 路径。','', '## 已完成运行的原指标','']
for r in rows:
    if r['status']['status']=='complete':lines+=['- `'+r['run']+'`: `'+json.dumps(r['native_metrics'],ensure_ascii=False)+'`']
(base/'docs/run-records.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'runs':len(rows),'status':dict(Counter(r['status']['status'] for r in rows))}))
