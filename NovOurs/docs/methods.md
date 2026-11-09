# 方法与复现边界

来源方案：[Notion 11月初受控 pilot 设计](https://www.notion.so/3ff200d7109280699628d1cf59d08625)。快照见 `notion-spec.md`。

本目录实现的是原生环境接入与任务泛化后的方法实验代码，不把跨任务改写称为原作者的官方实现或论文成绩。所有 planning utility 都是 agent 的内部估计，不参与原 benchmark 最终评分。所有内部模型调用使用 actor 配置并写入日志；与环境用户/judge分离。

- `native`：各来源自己的 assistant/NanoBot。LifeSim 原偏好记忆与其问答、意图预测调用保留。Pi 使用原 NanoBot 与原工具。
- `direct`：无额外状态模块的独立通用 harness；具有完整公开交互历史，可自主问询、回应或选择环境提供的工具。
- `stateforge`：按[论文 §7](https://arxiv.org/html/2609.32520v1)重实现状态折叠、显式/派生要求、传递依赖失效，以及独立格式跟踪/检查/一次重生成。提示词由本项目编写；不是作者代码。
- `voi`：按[论文 §4](https://arxiv.org/html/2601.06407v1)及官方 `flight_rec/voi_utils.py` 的 expected post-answer value minus current value minus question cost 泛化到自然语言意图/动作。去掉原航班固定特征与固定选项；当前实现使用逐假设预测回答、重新估计后验和动作收益，因此是任务泛化版，非原航班实验逐行复现。
- `revoir`：按[论文 §3](https://arxiv.org/html/2609.37588v1)重实现联合意图粒子、语义一致性权重、候选行动、假想回答/后验、提问价值，以及用户可纠正时的行动后反馈价值。当前采用 joint + batch rescoring；没有冒称 factored/incremental 版本。新环境采用自编提示词与有限候选；预算与成本显式配置。
- `stitch`：官方提交 `1115129590410e90cb7fe84c57098f9d404c56a9` 的 `rank_turns_by_representativeness` 原函数直接加载。在线 scope/event/entity 标签与引用解析、原标签密度排名、CPU embedding 语义检索接入当前消息。当前不复现作者完整 DSPy/Qdrant 调度、连续片段合并和 usefulness 二次过滤，故这是 **STITCH-adapted**，不能作为官方 STITCH 完整复现的替代。完整官方流水线可经外部 agent 接口接入。
- `stitch_official`：调用同一锁定提交的原 description、scope、segment notes、event labeler、turn notes、label retrieval 入口；保留原提示和筛选排序。仅导出已观察历史，使用原程序支持的无Qdrant文件模式、本地Qwen embedding和Qwen actor。`stitch_official_revoir` 将同样的原检索结果接入REVOIR。隔离依赖见 `setup_stitch.sh`；是否试跑成功以 `run-records.json` 为准。
- `stateforge_revoir`、`stitch_revoir`：本项目构造的组合基线；状态或检索上下文进入共同 REVOIR 决策器。
- `p1`：证据约束的多个适用性解释，共同默认问题生成/决策模块；检查候选行动是否在所有解释下都被估计为可接受。
- `p2`：保持共同粒子/决策模块，仅将问题生成集中于 scope/revision 边界。
- `p3`：P1+P2，实际回答与反馈进入后续持久状态；假想回答只保存在 planning 日志，不写入真实用户历史。支持 `ablate` 中移除 `source_ids`、`scope`、`revision_of` 做诊断。解释交集为空不强制提问。
- `in3`：需要已公开的 Mistral-Interact 权重与原 inquiry→summary→executor 流程；不以普通 Qwen 提示词冒充。已实现原 SYS_PROMPT 与 `[INQUIRY]/[SUMMARY]` 协议接入；必须在 `agent.inquiry` 配置原 `hbx/Mistral-Interact` checkpoint 的服务。未部署该权重时显式报缺资源，不能用普通 Qwen 代替。
- `capture`：方案中标注原训练组件/权重尚缺；明确拒绝运行该名称，不提供伪替代。

默认 smoke 使用 2 个意图假设、2 个行动、1 个问题候选及最多 2 次提问，只是低成本联调参数，不是论文推荐参数。`question_cost=0.1`、`action_cost=0`、`correction_cost=0.05` 为本项目内部决策超参，不能用它们构造新的 benchmark 总分。

模型输出能力或证据ID违规时，最多一次带验证错误的重生成；第二次仍违规即失败。不会静默把工具改成回应、删除错误事实或把假想反馈作为真实观察。该修复调用计入日志和预算。

IR 是 LifeSim 特定诊断字段：自定义 harness 可返回 `diagnostics.intent`。未提供时按原 scorer 的空预测处理，不能把缺失诊断解释成经过验证的意图推断错误；系统报告须标明诊断覆盖率。
