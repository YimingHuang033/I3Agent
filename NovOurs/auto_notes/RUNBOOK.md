# 运维执行手册：从登录到交付

适用主机：BBQCard2；目录：`/home/tim/Proj/I3Agent`。本手册的命令在服务器执行。先看 [实验计划](README.md)；本次文档更新只准备计划，不代运维启动付费模型实验。

## 1. 更新和检查，不调用模型

```bash
ssh BBQCard2
cd /home/tim/Proj/I3Agent
git status --short
# 工作区有修改时先检查，不reset/clean覆盖他人的工作
git pull --ff-only
git submodule status
nvidia-smi
df -h .
test -r deepseek.env.sh
test -d /mnt/data/Qwen3-8B
test -d models/Qwen3-Embedding-0.6B
test -x lifesim-venv/bin/python
test -x .venv-pibench311/bin/python
test -x NovOurs/.local/venv/bin/python
test -x NovOurs/.local/stitch-venv/bin/python
```

已有验证环境见 [environment.json](../docs/environment.json)。缺MemPA隔离环境时执行 `bash NovOurs/setup_mempa.sh`；缺STITCH源码时执行 `python3 NovOurs/setup_upstream.py`，然后 `bash NovOurs/setup_stitch.sh`。这两个安装入口仅用于准备，不要每次重装；不要向conda `tim` 执行pip升级。STITCH源码快照若无`.git`，setup_upstream会保留为备份再clone；遇到既有备份应先核查，不要自动删除。

```bash
PYTHONPATH=NovOurs NovOurs/.local/venv/bin/python -m unittest discover -s NovOurs/tests -v
PYTHONPATH=NovOurs lifesim-venv/bin/python -m novours inventory --output NovOurs/.local/inventory-ops.json
```

当前基线是13项契约测试通过；后续代码若增加测试，以全部通过为准。缺子模块/数据或测试失败先修环境，不开始A。inventory里的ProAgent skipped是已知资源缺口，不是让运维补造评分。

## 2. 冻结本批计划，不调用模型

```bash
export NOVOURS_CAMPAIGN="$PWD/NovOurs/.local/campaigns/$(date +%Y%m%d-%H%M%S)"
python3 NovOurs/auto_notes/prepare_plan.py --output "$NOVOURS_CAMPAIGN"
printf '%s\n' "$NOVOURS_CAMPAIGN" > NovOurs/.local/active-campaign
export NOVOURS_RUN_ID="$(basename "$NOVOURS_CAMPAIGN")"
git rev-parse HEAD > "$NOVOURS_CAMPAIGN/code-commit.txt"
git submodule status > "$NOVOURS_CAMPAIGN/submodules.txt"
```

输出应为 `jobs: [9, 600, 10]`、`model_calls: 0`。目录内有 `A-regression.json`、`B-lifesim.json`、`C-pi.json`、`selection.json`、`excluded.json`、`coverage.jsonl`、`campaign.json`。excluded记录被排除的歧义重复ID；当前long_horizon有119个。固定events和users源文件散列。不自动生成D；完整MemPA存在非连续acc选择接入缺口，详见实验计划。脚本拒绝覆盖既有目录。

换终端后恢复变量：

```bash
cd /home/tim/Proj/I3Agent
export NOVOURS_CAMPAIGN="$(cat NovOurs/.local/active-campaign)"
export NOVOURS_RUN_ID="$(basename "$NOVOURS_CAMPAIGN")"
export PYTHONPATH="$PWD/NovOurs"
```

生成器直接写入现有 `pilot.py` 支持的plan格式。抽样使用固定种子、排序后的ID，保存60条原记录及散列；它不判断研究覆盖类别。研究人员应在模型结果出现前完成coverage审查，运维不代填标签。不要修改已经开跑的plan、源文件或代码；变更应生成新批次，保留旧失败记录。

## 3. 启动一台vLLM服务

先确认GPU与8012端口没有被其他任务占用；已有兼容Qwen服务可以复用。以下以空闲GPU1为例，所有新生成的计划都使用8012；不需要另开8011。

```bash
systemd-run --user --unit=novours-pilot-vllm \
  --working-directory="$PWD" \
  --setenv=NOVOURS_GPU=1 --setenv=NOVOURS_PORT=8012 \
  --setenv=NOVOURS_CONTEXT=32768 --setenv=NOVOURS_GPU_MEMORY=0.93 \
  --setenv=NOVOURS_SEQUENCES=8 \
  /bin/bash NovOurs/launch_vllm.sh
journalctl --user -u novours-pilot-vllm -n 60 --no-pager
curl --fail --silent --show-error http://127.0.0.1:8012/v1/models
```

等GET成功后再运行A，返回模型ID应为Qwen3-8B；检查日志中的32768上下文。端口已占用时核对所属任务，不kill占用进程。此launcher固定Qwen的tool/reasoning parser，不能只改模型路径就声称支持GPT-OSS。若没有空闲GPU，可等待；不要直接把主矩阵换成DeepSeek并混入同一批结果。

检查凭据是否可载入，**不打印值**：

```bash
set -a
. ./deepseek.env.sh
set +a
python3 -c 'import os; assert os.environ.get("MODEL_API_KEY"), "Missing MODEL_API_KEY"; print("Credential variable present")'
```

变量存在不证明API授权有效；A的首个真实请求验证授权。不要set -x、cat凭据文件或把环境完整导出到日志。Pi需要网页搜索时使用已有BRAVE_SEARCH_API_KEY；工具报缺凭据时停该来源排查，不把工具失败算完成。当前C未使用AppWorld任务，未来添加前需独立验证其服务和工具schema。

## 4. 依次运行A、B、C

以下命令会真实调用模型。systemd保留进程组，SSH断开不丢任务；原始日志在`.local`，不上传到Git。

```bash
systemd-run --user --unit="novours-${NOVOURS_RUN_ID}-A" \
  --working-directory="$PWD" --setenv="NOVOURS_CAMPAIGN=$NOVOURS_CAMPAIGN" \
  /bin/bash -lc 'set -a; . ./deepseek.env.sh; set +a; export PYTHONPATH="$PWD/NovOurs"; exec python3 NovOurs/pilot.py run --plan "$NOVOURS_CAMPAIGN/A-regression.json" --output "$NOVOURS_CAMPAIGN/runs/A"'
```

查看 `runs/A/progress.json` 和各job的 `status.json`。完成条件：9个job都完成、原生工具实际初始化成功、LifeSim/Pi有原评分产物、MemPA是完成的原会话。A中MemPA `aggregate_scores=null`符合smoke定义；它不是完整研究结果。若某来源失败，先检查其job日志再决定修复，不能只看服务退出或finished计数。

B前须完成coverage审查。下面只校验标签/引用已填，不能替代研究人员判断证据是否成立：

```bash
python3 - <<'PY'
import json, os
from collections import Counter
from pathlib import Path
p=Path(os.environ['NOVOURS_CAMPAIGN'])/'coverage.jsonl'
rows=[json.loads(s) for s in p.read_text().splitlines()]
allowed={'persistent_default','one_off_exception','scoped_rule','revoked_or_revised','other_context','insufficient_evidence','not_applicable'}
assert len(rows)==60
assert all(r['review_status']=='reviewed' and r['category'] in allowed and r['evidence_refs'] for r in rows)
counts=Counter(r['category'] for r in rows)
assert all(counts[k]>=5 for k in ['persistent_default','revoked_or_revised','insufficient_evidence']), counts
print(dict(counts))
PY
sha256sum "$NOVOURS_CAMPAIGN/coverage.jsonl" > "$NOVOURS_CAMPAIGN/coverage.sha256"
```

B之前先用同批配置做一条**两轮官方STITCH**单独验收，用于确认冷缓存请求与吞吐，不计入主比较：

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ['NOVOURS_CAMPAIGN'])
jobs=json.loads((p/'B-lifesim.json').read_text())['jobs']
cfg=next(j['config'] for j in jobs if j['config']['agent']['method']=='stitch_official')
(p/'stitch-preflight.json').write_text(json.dumps(cfg,indent=2)+'\n')
PY
PYTHONPATH=NovOurs lifesim-venv/bin/python -m novours run \
  --config "$NOVOURS_CAMPAIGN/stitch-preflight.json" \
  --output "$NOVOURS_CAMPAIGN/stitch-preflight"
```

该命令在前台运行，等结束后再断SSH；API变量沿用第3节。确认其status=complete且trace包含actor_stitch实际请求，查看各轮独立dspy_cache。若失败，先修官方STITCH接入，不用轻量stitch替换同名结果。

条件满足后启动B；B结束并确认Pi在A通过后启动C，**不要把以下两条同时提交**：

```bash
systemd-run --user --unit="novours-${NOVOURS_RUN_ID}-B" \
  --working-directory="$PWD" --setenv="NOVOURS_CAMPAIGN=$NOVOURS_CAMPAIGN" \
  /bin/bash -lc 'set -a; . ./deepseek.env.sh; set +a; export PYTHONPATH="$PWD/NovOurs"; exec python3 NovOurs/pilot.py run --plan "$NOVOURS_CAMPAIGN/B-lifesim.json" --output "$NOVOURS_CAMPAIGN/runs/B"'

# B结束后再执行C
systemd-run --user --unit="novours-${NOVOURS_RUN_ID}-C" \
  --working-directory="$PWD" --setenv="NOVOURS_CAMPAIGN=$NOVOURS_CAMPAIGN" \
  /bin/bash -lc 'set -a; . ./deepseek.env.sh; set +a; export PYTHONPATH="$PWD/NovOurs"; exec python3 NovOurs/pilot.py run --plan "$NOVOURS_CAMPAIGN/C-pi.json" --output "$NOVOURS_CAMPAIGN/runs/C"'
```

## 5. 监控、故障处理与停止

```bash
journalctl --user -u "novours-${NOVOURS_RUN_ID}-A" -n 80 --no-pager
cat "$NOVOURS_CAMPAIGN/runs/A/progress.json"
# B/C运行时将A换成相应阶段；某job详情在阶段目录/<job-id>/
```

`pilot.py`会在一个job失败后继续下一项；持续失败时运维应主动停止本批，而不是等待它耗尽整个队列。查看job的 `status.json`、阶段目录的 `<job-id>.log`；MemPA另有job/native.log，STITCH另有job/stitch_official/<hash>/pipeline.log。

- 401/403：重新配置对应服务凭据，不将key写入config/Git。429：先停本批，等待服务恢复后另行安排，默认不提高并发。
- connection refused：检查8012服务及模型名。context length/截断：记录原输入规模和预算，调整后新建批次；不要私自删历史后沿用原实验名。
- MemPA MCP报错：使用 `.local/venv/bin/python`，mcp必须1.x；不能因CLI退出0就忽略工具初始化失败。`acc_016`等不存在或缺probe：完整时间线选择未接好，D仍处于阻塞状态。
- `needs_inspection`：这是不完整运行保护，不是成功，也不是已自动续跑。停止后不要删除manifest冒充新运行。
- 分数为0：先确认原评分产物完整；模型表现差与工程失败分别报告，不为了高分反复重跑同一任务。

```bash
# 只停止本批对应阶段；systemd默认会处理该服务的整个进程组
systemctl --user stop "novours-${NOVOURS_RUN_ID}-B"
# 全部模型任务结束、且确认没有他人复用本服务后，才停止本次vLLM
systemctl --user stop novours-pilot-vllm
```

中断可能使status保留running；须结合systemd/进程确认，记录中断原因，不能把running当仍在推进。重新执行原plan仅复用已有result；未完整交互的job会needs_inspection，需新目录重新运行并记录retry关系，不保证逐轮续跑。

若**交互日志完整、仅评分失败**，可使用冻结配置单独evaluate。例如LifeSim：

```bash
PYTHONPATH=NovOurs lifesim-venv/bin/python -m novours evaluate \
  --config "$NOVOURS_CAMPAIGN/runs/A/configs/lifesim-p3.json" \
  --output "$NOVOURS_CAMPAIGN/runs/A/lifesim-p3"
```

先核对原日志事件/轮次数与config一致；evaluate只读到一条残留日志不证明原交互全部完成。LifeSim复用已存在judge文件；不要直接复用损坏/空judge文件。Pi用 `.venv-pibench311/bin/python`；MemPA用 `.local/venv/bin/python`，且只有完整原probe可评分。不要把failed的acc001会话送去宣称完整评分。

## 6. 交付与归档

```bash
PYTHONPATH=NovOurs lifesim-venv/bin/python NovOurs/report_runs.py
git status --short
```

report_runs会重建 `docs/run-records.md/json`，范围是所有`.local`运行，不只本批；按run路径前缀筛选本批。它输出运行账本，不会自动做研究配对分析，`eligible_for_smoke_claims`也不是正式实验有效性证明。

交接时给出：代码提交、campaign/计划散列、selection与coverage散列、三阶段进度、成功/失败/skip分母、各来源原指标、人工证据诊断及调用/token/耗时，并单列重试与缺资源项。MemPA全量仍阻塞时明确写出，不能填0代替未测。所有模型API调用（含STITCH内部）、缓存范围、实际后端和intent诊断覆盖都应披露。

凭据、虚拟环境、完整原始对话/轨迹、私有runtime副本留`.local`；上传代码、无密钥配置与审核后的汇总。原benchmark子模块和旧ours结果不改；旧DeepSeek全轨迹审计保持停止。生成计划/写文档本身不会启动它。
