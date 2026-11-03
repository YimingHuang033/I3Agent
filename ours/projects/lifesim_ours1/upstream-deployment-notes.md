# LifeSim 在 BBQCard2 的部署、改动与最小试跑记录

## 1. 目标与基线

- 官方源：`https://github.com/sii-research/lifesim.git`
- 基线 commit：`44e3cb8fa26d296a9a29c663035ea7d2f7370272`。
- 部署目录：`/home/tim/Proj/I3Agent/lifesim`。
- 本次目标：只跑一个 `single_session` 原始序列的第一个事件，执行原版两轮对话，再执行原版七项裁判评估与分数聚合。不是全量复现，也不作为排行榜结果。
- 模拟用户、被测助手、裁判都使用 `deepseek-flash`；凭据从仓库外 `../deepseek.env.sh` 读取，不写入代码、日志或本文。

### 获取方式说明

- 同目录有官方 bundle `../lifesim.bundle`，其 HEAD 为上述 commit。
- 本机从该 bundle 直接 `git clone` 报 `early EOF`，未成功生成仓库。
- 实际部署使用同目录的 `../lifesim-runtime.tar.gz` 解包，因此当前 `lifesim/` 没有 `.git` 元数据。
- 未对 tar 与 bundle 做逐文件哈希比对；tar 内容按同批部署资料使用。

## 2. 相对原版的改动

只做运行所必需的兼容与安全改动，未改任务数据、隐藏意图、模型提示词、评分提示词或指标定义。

1. `src/models/__init__.py`
   - 在 `DEEPSEEK_MODELS` 中加入 `deepseek-flash`。
   - DeepSeek 分支把调用方的 `base_url` 传给构造函数；原版只识别 `deepseek-chat` / `deepseek-reasoner`，且不传递自定义 endpoint。
2. `src/models/cloud.py`
   - `DeepSeek.__init__` 增加可选 `base_url`，缺省仍使用官方地址。
   - 同时兼容原版 eval factory 传入 `base_url` 的调用方式。
3. `src/main_mp.py`
   - 用户/助手 API key 的默认值改为读取 `USER_API_KEY` / `MODEL_API_KEY`，仍保留显式 CLI 参数。
   - 启动参数日志对包含 `api_key` 的字段做 `[REDACTED]`，避免把凭据写入 `simulation.log`。
4. 新增 `scripts/run_minimal_bbqcard2.sh`
   - 固定为单序列、单事件、单线程、两轮对话。
   - 串联原版 `src/main_mp.py` → `src/evaluation/eval.py` → `src/evaluation/metric.py`。
   - 额外支持 `LIFESIM_RUN_DIR`、`LIFESIM_MODEL`、`LIFESIM_EMBEDDING`、`LIFESIM_PYTHON` 环境变量。
   - 使用仓库外的 `../lifesim-venv`，不要求在 `lifesim/` 内再建 `.venv`。
5. 新增 `scripts/verify_minimal.py`
   - 原版入口可能吞掉单个事件的异常并以 0 退出，不能只看退出码。
   - 本脚本检查 `sim_log_*.json` 中确实存在非空的 user/assistant 对话。
   - 已修复一次误把 JSONL 当单个 JSON 解析的问题；现在同时支持单个 JSON 和逐行 JSONL。
6. 新增 `outputs/environment-freeze.txt`
   - 记录当前 venv 的包版本快照，用于追溯，不是跨机器锁文件。
7. 新增 `modify.md`
   - 本文件。

## 3. 环境与资源

- 解释器：`/home/tim/Proj/I3Agent/lifesim-venv/bin/python`，Python 3.11.14。
- venv 使用 `--system-site-packages`，复用现有 conda `tim` 环境的 PyTorch、transformers、sentence-transformers 等；新增包只装进 venv。
- 原版 `requirements.txt` 含大量 vLLM/CUDA 训练依赖，本次没有整体安装；只安装本次 API + CPU embedding 链路需要的核心包。
- 关键版本：`openai 3.24.0`（系统环境）、`chromadb 1.2.0`、`torch 2.13.0+cu130`（本次未用 GPU）、`sentence-transformers 6.1.0`、`transformers 5.18.0`、`json_repair 0.52.2`、`editdistance 0.8.1`、`numpy 2.2.6`。
- embedding：`/home/tim/Proj/I3Agent/models/Qwen3-Embedding-0.6B`，1.2 GiB，按原版入口在 CPU 上运行。
- 数据：仓库自带 `data/single_session` 与 `data/long_horizon`，未使用 mock 对话或随机 embedding。
- 资源规模：运行时机器约 32 vCPU、125 GiB RAM、约 149 GiB 可用磁盘；本试跑只使用 1 个事件、1 个线程、CPU embedding，未使用 GPU、Docker、AppWorld、网页搜索或真实应用账号。
- 现有 venv 中 `openai 3.24.0` 与系统里某个 `langchain-openai` 的版本约束不完全一致，但该冲突包不在本次运行链路中；`pip check` 仅有这一条系统级提示。

## 4. 实际试跑与结果

### 第一次尝试

- 仿真本身成功：1 个序列、1 个事件、2 轮、4 条对话。
- 流水线在 `scripts/verify_minimal.py` 处退出，原因是校验脚本把多行 JSONL 当成单个 JSON 解析；不是模型或仿真失败。
- 产物保留在 `outputs/minimal-20261031-204637`，未作为最终端到端结果。

### 修复后完整重跑

- 运行目录：`outputs/minimal-20261031-204933`
- 外层日志：`../setup-logs/minimal-20261031-204933.log`
- 运行时间：2026-10-31 20:49:33 → 20:51:35（约 2 分 2 秒）
- 仿真：`Success: 1`，`Failure: 0`；1 个序列、1 个事件、2 轮。
- 对话产物：`logs/main_user_deepseek-flash_assistant_deepseek-flash_V2_single_session/logs_0/sim_log_*.json`
- 七项指标（`scores.json`）：

```json
{
  "IR_explicit": 0.0,
  "IR_implicit": 0.0,
  "IC_explicit": 0.0,
  "IC_implicit": 0.0,
  "NAT": 60.0,
  "COH": 60.0,
  "PA": 28.6,
  "EA": 60.0,
  "RR": 0.0
}
```

- 指标位置：`outputs/minimal-20261031-204933/metric_outputs/main_user_deepseek-flash_assistant_deepseek-flash_V2_single_session/scores.json`
- 该次结果只证明原始 LifeSim 的仿真 → 七项裁判 → 聚合链路在本机可跑通，不代表完整 LifeSim-Eval 的性能。

## 5. 当前资源与结论限制

- 只跑 1 个事件，不能证明长程记忆、跨事件一致性、多会话累积或全数据集表现。
- `single_session` 的单事件、单线程只是最小 smoke；原版默认的 `n_events_per_sequence` 和多线程行为未验证。
- embedding 在 CPU 上运行，速度受限；本次没有使用 GPU 本地推理。
- 模拟用户、助手、裁判共用 `deepseek-flash`，存在同模型自评偏差；不能直接与论文的 Qwen/GPT 判分配置比较。
- 原版运行时可能吞掉个别事件异常，故必须结合 `verify_minimal.py`、`simulation.log` 和实际 `dialogue` 判断，而不是只看退出码。
- 本次没有运行 `long_horizon`、全量 120 个 single_session 序列、全量 1309 个 long_horizon 事件或全量 `requirements.txt` 中的训练栈。

## 6. 复现入口

```bash
cd /home/tim/Proj/I3Agent/lifesim
LIFESIM_RUN_DIR="$PWD/outputs/minimal-$(date +%Y%m%d-%H%M%S)" \
  bash scripts/run_minimal_bbqcard2.sh
```

脚本会执行仿真、校验、七项评估和指标聚合，并在最后打印运行目录。需要重新选择事件时，修改 `scripts/run_minimal_bbqcard2.sh` 中的 `SEQ` 取值；当前固定为 `data/single_session/events.jsonl` 的第一条。

## 7. long-horizon 小样本验证（2026-11-01，已完成）

### 数据语义与运行范围

- 原版 `data/long_horizon/events.jsonl` 有 1309 行，每行 events 长度为 1；历史上下文通过事件中的 conv_history 注入 AssistantAgent 的 system prompt。不是把 n_events_per_sequence 设置成 10 来模拟十个未来事件；那样会数组越界，且可能被原版捕获后误报成功。
- 本次选择历史长度分别为 11、6、3 的三条原始记录，每条执行 1 个事件、2 轮交互，n_threads=1，保持原版用户配置和助手记忆开关，沿用 DeepSeek 三角色及 CPU Qwen3 embedding。
- 发现原数据有重复 sequence ID，OfflineLifeEventEngine 的 id2events 字典会保留最后一条；本次只选唯一 ID，不修改原数据，不擅自拼接不同用户或历史变体。
- 七项评分仍使用原版 eval.py / metric.py，两个裁判线程。此实验测试预置长期历史条件下的运行链路，不验证在线跨事件记忆形成或全量结果。

### 新增文件

- scripts/long_horizon_selection.json：三个输入 ID 及历史规模，便于复现。
- scripts/run_long_horizon_bbqcard2.sh：由现有最小脚本派生，切换数据集和 ID 列表、保留每条一个事件，使用独立时间戳输出目录，记录起止时间并执行验证器。
- scripts/verify_long_horizon.py：检查三条完整对话、每条四条非空消息、实际助手请求中的历史注入、七项裁判各三条非空输出及最终九个汇总字段；生成 verification.json。
- 不修改模型逻辑、原始数据、模拟/评分提示词或指标定义。

选定输入：
```json
[
  {
    "sequence_id": "281646223_2144_TKY_sport_health_6_0_0",
    "user_id": "281646223_0_0",
    "history_entries": 11,
    "history_characters": 19636
  },
  {
    "sequence_id": "281646223_2144_TKY_sport_health_6_0_5",
    "user_id": "281646223_0_5",
    "history_entries": 6,
    "history_characters": 10722
  },
  {
    "sequence_id": "281646223_2144_TKY_sport_health_6_0_8",
    "user_id": "281646223_0_8",
    "history_entries": 3,
    "history_characters": 6652
  }
]
```

验证器兼容原版不同指标的 sequence_id 存放位置（顶层或 conv 内），并检查裁判 JSON 可解析、评分字段范围及汇总值有限；这只加强结果校验，不改变原版分数。

### long-horizon 实际结果：已完成并核验

- 输出目录：`outputs/long-horizon-20261101-230752`。
- 仿真开始：2026-11-01T23:07:52+08:00；分数文件生成：2026-11-01T23:15:07.023050+08:00。主链路约 435 秒（根据起始记录与分数文件 mtime）。
- 完成 3 条原始样本，每条 1 个事件、2 轮，共 12 条非空对话消息；仿真报告 Success: 3 / Failure: 0。
- 七项裁判各产生 3 条非空且可解析的输出，共 21 条；检查评分字段范围合法、汇总数值有限。
- 三条样本的 11 / 6 / 3 段历史均在保存的实际助手 API 请求 system 消息中逐段找到，见 verification.json。
- 原版 main_mp.py、eval.py、metric.py 已执行完成，未改评分语义。

```json
{
  "IR_explicit": 100.0,
  "IR_implicit": 0.0,
  "IC_explicit": 100.0,
  "IC_implicit": 0.0,
  "NAT": 86.7,
  "COH": 86.7,
  "PA": 54.8,
  "EA": 86.7,
  "RR": 0.0
}
```

### 校验器问题与恢复

- 首次外层退出码为 1，发生在所有仿真与七项评分、聚合完成后：新增验证器远程文本替换时引号被 shell 处理，造成语法错误。
- 修复为传输完整文件后，进一步修正各指标 sequence_id 的读取：IR/IC 在顶层且 conv 是字符串，其他指标在嵌套 conv 对象中。避免 dict.get 默认参数的提前求值。
- 修复后仅对已有产物重跑验证器，退出码 0，不重新生成对话或裁判分数。
- 保留原 `outputs/long-horizon-exit-code.txt` 的 1 和启动日志，另存本次产物目录的 verification-exit-code.txt（0）、verified_at.txt、verification.json，以区分原始启动状态和最终校验状态。
- 最终校验时间：2026-11-01T23:17:42.186960+08:00。

### 复现与结论边界

```bash
cd /home/tim/Proj/I3Agent/lifesim
bash scripts/run_long_horizon_bbqcard2.sh
```

脚本采用独立时间戳目录，已修复验证器。此次三条样本属于同一运动健康场景的历史长度变体，并非三个独立主题；不据此做显著性或质量排名。它证明原版预置长期历史的模拟→裁判→聚合链路可用，不代表全量 1309 行、在线多事件记忆累积或所有历史长度均已验证。数据的 119 组重复 ID 尚未修复，正式全量前需要决定保留/去重/重编号协议；本次选择均为唯一 ID。
