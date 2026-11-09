# NovOurs 实验计划与运维交接

更新：2026-11-10。运维按 [RUNBOOK.md](RUNBOOK.md) 执行；本页说明为什么跑、跑多少、什么情况下可以扩量。依据为仓库保存的 [Notion 11月初方案及11月9日补充](../docs/notion-spec.md)，结合 `d090f67` 的实测结果和本次代码核查。这里的新批次尚未执行，不把旧联调成绩当正式pilot。

## 研究问题与固定原则

区分“仍有效但本轮省略的历史偏好”与“已经被修改、撤销或限定范围的旧偏好”。检验P1的适用性解释、P2的边界澄清、P3的持续修订是否改善原任务表现。行动正确性使用原评分；无依据假设和提问负担作为可追溯诊断，不另造跨benchmark总分，不训练模型。

参评对象为完整harness＋model。每个来源内固定任务、初始状态、公开信息、模拟用户、工具权限和预算；保留原会话顺序与probe隔离。隐藏目标只给原用户模拟器/评分器，人工覆盖标签不传给actor。

本次主矩阵固定Qwen3-8B/vLLM（32K、8012），用户与judge固定DeepSeek `deepseek-v4-flash`，temperature=0，单次输出上限4096。调度并发1；官方STITCH内部可能并发请求，不能把调度并发当API并发。模型或预算变更必须新建批次，不混算。

## 阶段与明确任务量

**A：回归与接入验证，9个job。** LifeSim一条single_session记录、Pi `researcher_task_011`、MemPA `user_a/acc_001`，各跑native/direct/p3。LifeSim每条1事件、2轮；Pi上限12轮、每轮工具循环上限40次迭代（不等同40个工具调用）；MemPA `score=false`、900秒超时。MemPA/Pi的P3尚未有对应来源的通过记录，A正用于发现这些问题。某来源出现协议/工具错误，只停止该来源扩量；不得把退出0且工具初始化失败当作通过。

**B：主要意图推断pilot，60条LifeSim原记录 × 10种方法 = 600个job。** single_session与long_horizon各30条，以固定种子20261110从按ID排序的原记录中抽取。每条1事件、2轮；选样清单和源文件散列随计划落盘。方法是native、direct、stateforge、voi、revoir、stateforge_revoir、stitch_official、p1、p2、p3。`stitch_official`使用原流水线；轻量`stitch`不替代它。

数据检查发现long_horizon的1309行中有119个重复sequence_id（各出现2次）；native按ID加载存在歧义，因此生成器排除这些ID的全部行，保留1071条无歧义记录作抽样池。single_session的120个ID均唯一。排除清单写入 `excluded.json`，不改原数据；不能把本批称作覆盖整个发布集。

执行B前，研究人员完成 `coverage.jsonl` 的盲于模型结果的覆盖审查：category填 `persistent_default`、`one_off_exception`、`scoped_rule`、`revoked_or_revised`、`other_context`、`insufficient_evidence` 或 `not_applicable`；附原字段/轮次引用，review_status改为reviewed。重点检查长期默认、撤销/修改、证据不足各至少5条；不足时先调整并重新冻结任务清单，不能由运维猜标签或补造纠正。没有足够覆盖时只做描述性接入实验，不得宣称验证了主研究假设。

同一任务跨方法配对比较；这**不是**只改变一条偏好的人工反事实任务对。若要主张历史省略/纠正的因果效应，还需研究人员选择有原生依据的匹配任务组并记录匹配依据。生成器不伪造这种配对。

当前direct含完整公开交互历史，不是“仅当前消息”基线。纯current-only和额外历史检索消融尚未加入本矩阵；需单独实现、验证并重新冻结计划后才能以该名称报告。

**C：工具场景迁移，1条Pi任务 × 相同10方法 = 10个job。** 仍用原有task011和原评分。C是工具接入对照，不作大样本结论；其他Pi任务、AppWorld和依赖任务序列在核查工具资源、原依赖顺序后另冻清单。不能把task011结果外推全部100个任务。

**D：MemPA长期验证，暂缓执行。** 后续目标为user_a/user_b两条完整persona时间线 × native/revoir/stateforge_revoir/p3四方法，共8条完整运行，每条需原33 probes及原聚合。当前adapter只传 `--acc-range`；原来源的完整时间线是99个非连续acc，散布在001–108，中间有9个probe槽，原CLI用 `--acc-list` 表达。**不能把 `acc_range=1-108, score=true` 当作可执行全量配置。** 必须先补接原显式acc清单/计划与probe流程，检查原计划和33-probe覆盖，再做一条完整persona验收。此阶段不在自动生成的可执行计划中。

**ProAgent / IN3 / CAPTURE：资源等待。** ProAgent保持原逐条skip清单，缺原评分目标、evaluator、截图和部分LFS源文件时不评分；IN3需原Mistral-Interact服务；CAPTURE需原训练组件。GPT-OSS和DeepSeek actor扩展留作第二批，先独立完成各来源回归，不冒称已有同模型完整对比。

## 分析与验收

- 原指标分别报告：LifeSim原七项judge路径及聚合，Pi checklist/proactiveness及原工具验收，MemPA仅在完整probe产物齐备时报告原指标。不同来源不合成总分。
- B按setting、覆盖类别及同一sequence_id做配对差值；同时列完成/失败/跳过分母。失败不能静默删除或挑选多次重跑中的最高分。当前只有一次重复，temperature=0也不等于确定性；有趋势后再冻独立重复批次。
- 无依据假设诊断需实际公开证据与行动引用；planning里预测的回答不是事实。问询负担报告显式ask次数，并人工检查问句是否被包装为respond。两者都不是新增官方得分。
- LifeSim自定义harness的IR/IC要同时报intent诊断覆盖率；当前long_horizon每条原记录只有1事件，不声称跨事件长期效果。P3跨会话主张需等待D。
- 每个job保留manifest、status、result、原生轨迹/文件、模型调用日志和原评分文件。总进度完成不等于全部成功；MemPA smoke完成不等于有完整指标。
- StateForge/REVOIR为论文重实现，VoI为任务泛化，详见 [方法边界](../docs/methods.md)。正式比较不能只用方法名暗示官方论文成绩。

## 资源与耗时安排

本轮准备脚本只生成619个job的三个计划，不发API请求、不启动GPU、不自动运行。正式执行按A→B→C；可复用单张空闲4090启动一台32K Qwen服务，所有生成配置都指向8012。原独立smoke配置仍可能指向8011，不要混用。

历史LifeSim两轮非官方STITCH方法约34–116秒/条，Pi native/direct约3–4分钟/条，MemPA acc001约67秒。B中540个非官方STITCH job据此粗算5–18小时；另60个官方STITCH job尚无同预算可靠吞吐估计，必须先跑一条两轮样本，再用实际耗时估算。加上C、模型冷启动、重生成和故障处理，不承诺一夜跑完。D没有可靠全量耗时估计。

运维每小时查看一次日志/状态与API错误；持续429、上下文超限、密钥失效、工具初始化失败时停止扩量并保留失败产物。完整步骤、运行与停止命令见RUNBOOK。历史记录在 [results.md](../docs/results.md) 和 [run-records.md](../docs/run-records.md)，不覆盖它们来伪装新实验已完成。

本交接包已在BBQCard2完成两次无API试生成：619个job数量、重复ID排除、样本唯一性、任务/配置散列、确定性抽样和拒绝覆盖检查均通过。RUNBOOK的bash代码块已做语法检查，本地文档链接已核对；这些检查没有启动实际A/B/C实验。
