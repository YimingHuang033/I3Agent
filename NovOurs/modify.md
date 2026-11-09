# NovOurs 修改记录

2026-11-09 启动；实现依据为 Notion「11月初受控pilot study设计」及该节11月9日补充，不复用旧 Ours 合成选择题得分。

## 独立布局

全部新代码、配置、文档位于 `NovOurs/`。原始 benchmark 子模块保持原提交；输出、原生运行副本、缓存、模型请求与凭据相关运行环境均放 `.local/` 并忽略入 Git。未修改 conda `tim` 包，未恢复旧 DeepSeek 全轨迹分析任务。

## 接入变化

- `core.py / agents.py / rpc.py`：统一公开事件/动作、生命周期、Python与进程/HTTP接口；所有远程消息只含公开上下文。能力由来源限定；工具名验证；网络失败、token 截断显式失败；记录调用耗时/token/实际后端。环境内的原有重试策略另外保留。
- LifeSim：直接调用原 `ConversationSimulator`、`UserAgent`、事件引擎。替换 assistant 对象，桥接只披露原 assistant 可见的 dialogue_scene/conv_history 和真实对话。偏好汇总使用原提示词与格式化器，仅透露维度名，隐藏值不传入 actor。保留全部七项 judge prompts 与原 metric functions。绕开原 `run_simulation` 的吞异常逻辑，单个 episode 错误即标记运行失败。native 对照保留原 AssistantAgent。
- Pi：复用原 `BenchmarkRunner/UserAgent`、NanoBot 工具、JsonStorageHook、TraceEvaluationRunner；native 与通用 harness 通过同一 channel 入口。不同 harness 的工具轨迹转成原 TurnRecord。原任务资产只复制到独立 workspace，原评分定义不改。
- MemPA：在每次运行的私有源码副本中，将 OpenRouter-only URL 指到本地透明 transport gateway，显式记录映射到 Qwen/DeepSeek 的配置。源码副本的 model request policy 加入试跑模型；原 timeline/probe/checkpoint/scorer不重写。额外 controller 状态保存在原 Session.metadata，随原 checkpoint复制。DeepSeek 不支持的 json_schema 传输降为 json_object，原解析/校验保留，该差异记录日志；模型替换与传输差异使试跑不可比官方 leaderboard。
- ProAgent：按发布文件逐事件生成 skip 原因；缺原 evaluator/评分目标/截图时不生成用户目标，不跑替代评分。
- 方法实现与未覆盖的官方组件逐项见 `docs/methods.md`。训练依赖不会伪装成无训练方法。

## vLLM 调试

已有 `tim` 的 vLLM 0.30.0 初次启动失败：找不到 nvcc；指定已有 cu13 目录后发现 compiler/header mismatch。最终只改变服务环境 `VLLM_USE_V2_MODEL_RUNNER=0`、`VLLM_USE_FLASHINFER_SAMPLER=0` 并使用 `--enforce-eager --max-num-seqs 16`，成功启动 Qwen3-8B；未安装/覆盖 `tim` 内的软件。

具体试跑记录、验收与剩余限制见 `docs/results.md`（生成后）。

## 11月10日联调修正

- Pi 通用harness的 trace session目录改为原 `YYYYMMDD_HHMMSS` 格式。原runner发出reset时，通用harness也清空对应会话状态；同一任务内部保留完整状态。原评分结果文件完整保留，统一日志补充原用户/judge请求（早期smoke的actor-only统计注明缺口）。
- Pi 工具与MemPA原提示会超过16K上下文；在第二张GPU独立启动32K Qwen服务、端口8012，不截短原任务提示。服务参数可由 `launch_vllm.sh` 环境变量重现。
- MemPA私有副本的未选择Mem0/MemOS后端改为延迟导入，避免file-memory实验强制安装无关后端。`.local/venv` 安装 MCP1.30.0、json-repair0.64.8；通过PATH让原MCP子进程使用同一隔离解释器。原tim环境不改。run前检查MCP主版本，防止原CLI把工具初始化失败继续当作会话完成。
- MemPA支持原score命令独立evaluate并刷新gateway端口；原scorer决定是否具备完整probe，不对缺失probe造分。外接进程/HTTP/Python controller必须支持checkpoint/restore，状态随原Session.metadata落盘，恢复原probe分支时同步恢复；缺接口显式报错。
- LifeSim事件数在任何模型请求前检查。当前long_horizon每条原记录只有1事件，试跑配置按原结构运行1事件，不拼接记录。原长记录的历史和私有用户材料仍交给原模拟器管理。
- 原模型返回非法能力或无依据source_id时最多一次格式/证据修复，完整记录请求；再次违规失败。规划的预测回答不写入真实状态。
- 增加 `verify_parity.py`，直接运行原LifeSim metric CLI，对同一原轨迹、同一缓存judge输出比较全部聚合值。增加真实原MemPA checkpoint隔离测试和HTTP生命周期测试。
- ProAgent inventory区分11626个event与3个无法解析的源文件；不把文件数当任务数。
- STITCH新增官方流水线独立入口，保留轻量版名字。上游依赖仅安装 `.local/stitch-venv`，固定dspy-ai2.6.27及实际dspy3.4.1、LiteLLM1.74.15避免未限定的新版本与原OpenAI版本约束长时间回溯；provider替换、本地embedding和文件模式均记入配置。每轮流水线产物留在该运行目录。
- `report_runs.py` 汇总成功与失败、调用/token/时间、原分数、任务配置散列；不生成跨benchmark总分。新增运行manifest记录实现文件散列；evaluate不覆盖原运行起始manifest。
- STITCH锁定版本内部调用仍使用 `load_turns(dataset, path)`，但原reader已改为 `load_turns(path)`；仅在子进程入口兼容旧参数，不改原reader/算法。实际dspy3.4.1在当前Pydantic下不能解析该入口的字符串 `List[str]` 注解，运行入口时去掉future annotations并立即解析类型；原文件不改。使用仓库自带protobuf生成文件，避免无关前端生成器要求系统protoc。
- 公开会话上下文也赋予 `cN` 证据ID，使来源已披露的conv_history可被P1/P3引用；仍不把隐藏profile/intent传入agent。官方STITCH导出保留公开上下文/工具反馈的原角色，不把它们伪装成用户说过的话。
- `pilot.py` 支持先冻结显式任务配置×方法矩阵、再顺序运行，按来源使用隔离解释器；未启动全量实验。增加外部MemPA缺checkpoint协议时拒绝运行的契约测试，总计13项。
- 官方STITCH的 `question_turn_ids` 按原筛选语义列出全部已观察候选turn，而非仅当前请求；不提供未来或隐藏答案turn。原retriever从structured-notes的上两级寻找turns.jsonl，因此将结构化notes放在运行目录的notes子目录，保持原读取逻辑。v5缺少此布局与完整候选集，明确从有效smoke结论中排除。
- 原STITCH序列化使用 `node_selected_turn_details`，adapter按原输出键读入；不重命名原产物。审计发现DSPy默认全局缓存会复用前次尝试响应，现通过已核实的 `DSPY_CACHEDIR` 将缓存隔离到单次运行的输入快照目录。v7为使用暖缓存的管线通过，不能将其调用量当作冷启动成本；另增DeepSeek actor的隔离缓存官方管线验证。
- Pi外部harness在disconnect时收到finish并保存agent_state；MCP连接建立后刷新公开工具schemas，避免初始化早于MCP连接时丢失工具。Pi原LLMClient保留原重试实现，smoke显式将尝试上限设为2；所有成功/失败请求计入后续日志。

## 11月10日运维交接计划

- 新增 `auto_notes/README.md` 与 `RUNBOOK.md`，集中说明研究目标、固定配置、分阶段数量、覆盖审查、运行/监控/停止、恢复限制及交付证据；已有smoke和新计划明确区分。
- 新增 `auto_notes/prepare_plan.py`，固定种子抽取LifeSim两个setting各30条，生成A回归9、B主要pilot600、C工具迁移10个job的冻结计划，使用现有pilot.py执行；统一Qwen服务为8012，保存任务ID、数据散列、配置散列及待审查覆盖模板。生成阶段不调用模型、不启动GPU，不新增评分或修改原任务。
- 核查原MemPA `scripts/run_orchestrator.py` 的 `_acc_names_from_list` 与CLI参数，确认完整persona是99个非连续acc、001–108间含probe槽。当前adapter未接acc-list，撤回旧README中直接设1–108即全量运行的错误指引；长期8条运行仅列后续目标，暂不生成可执行D计划。
- 主矩阵使用官方STITCH、固定两轮，轻量适配版和旧单轮/暖缓存联调分开；明确direct当前保留公开历史，不冒称“只看当前消息”基线。
- 此次只做计划生成、静态检查和仓库提交，不启动新实验，不修改原benchmark子模块或tim环境。
- 无API试生成暴露LifeSim long_horizon存在119个重复sequence_id（1309行、1190个不同ID）。计划生成器排除这些歧义ID的全部记录，从1071个无歧义ID中抽样，并保存excluded清单；固定events/users文件散列。不修改来源数据，也不声称抽样池等于整个发布集。
