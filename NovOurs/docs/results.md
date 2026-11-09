# 联调结果与验收边界

日期：2026-11-09 至 11-10；主机 BBQCard2；执行目录 `/home/tim/Proj/I3Agent/NovOurs`。Actor 为 `/mnt/data/Qwen3-8B` 的 vLLM 服务；用户模拟与评分使用现有 DeepSeek `deepseek-v4-flash`。没有训练，没有启动旧 DeepSeek 全轨迹审计。

## 已实际完成

- LifeSim：原生 assistant、direct、StateForge、VoI、REVOIR、StateForge+REVOIR、STITCH-adapted、STITCH-adapted+REVOIR、P1/P2/P3 均完成单事件两轮与七项原 judge 路径。long_horizon 的 P3 也完成一条原记录。完整原指标见 `run-records.md/json`。
- LifeSim 的独立JSONL进程harness和DeepSeek直接担任actor也通过真实交互及原评分；不仅是协议mock或用户/judge调用。
- `lifesim-stitch-official-v7` 完成原STITCH全流水线和LifeSim原评分。原label/usefulness过滤在本例移除所有候选后，走原语义检索回退，候选为全部2个已观察turn；未替换原回退逻辑。此smoke为1事件1轮，其他主要LifeSim smoke为2轮，不能将分数直接作为同预算方法比较。

STITCH v7复用了DSPy默认全局暖缓存中的既有模型响应，因此只证明整条管线组合通过，不作为冷启动调用量或耗时依据。最终代码已按输入快照隔离缓存；独立的 `lifesim-stitch-official-deepseek` 已完成原流水线及评分，共记录27次真实模型调用，其中17次为官方STITCH内部调用，未出现模型请求错误。
- Pi：`researcher_task_011` 的原 NanoBot 与外接 direct harness 均完成用户交互、原工具、原轨迹和 checklist/proactiveness 原评分。native 为 6/14 checklist、0.50 proactiveness；direct 为 1/14、0.00。这是单任务联调结果，不是方法优劣结论。
- MemPA：原生与外接 direct 在 `user_a / acc_001 / nanobot_file_memory` 完成原用户模拟、MCP 工具及原会话流程；约67秒。未运行全部33个 probes，因此没有 PSA/BRS/CS/PET 完整成绩。
- 13项契约测试在隔离的 Python 3.11 环境通过；包括原生 MemPA SessionManager checkpoint 的真实落盘/恢复和 probe 分支隔离、私有字段隔离、传递依赖撤销、假想分支不污染历史、工具能力、HTTP/JSONL生命周期。
- 同一 LifeSim 轨迹和缓存 judge 输出，由原 `metric.py` CLI 与 adapter 独立聚合，全部原指标一致。证据 `.local/runs/lifesim-native/parity_native_cli.json`。这项验证只覆盖该来源的评分聚合，不宣称全部工具轨迹或四个来源均通过 parity。

## 运行效率

在此次并行联调负载下，LifeSim 单事件两轮：direct约34秒，native约44秒，StateForge约46秒，VoI约49秒，REVOIR约65秒，P1约85秒，P2约57秒，P3约75秒；组合约74–116秒。P3 long_horizon一条约113秒。Pi 工具任务native约223秒、direct约182秒。

这些数字包含冷启动、模拟用户和评分；不是纯推理吞吐，也不能线性外推全量。规划方法一次环境行动会触发多次 actor 调用，例如 P3 smoke共记录66次模型调用，direct为14次。初期 Pi 统一日志仅包含actor，用户/judge的调用记录仍在原生日志；后来加入 LoggedClient 后统一日志也覆盖两者。

## 数据与资源限制

1. 当前 LifeSim `long_horizon/events.jsonl` 的1309条记录每条只有一个事件；single_session有120条。adapter检查事件上界，不把原runner吞掉的越界当作完成多个事件。原历史上下文仍保留，但本次不能据此声称已验证跨事件长期能力。
2. ProAgent当前有11626个可解析事件、3个未解析Git LFS源文件；缺原 evaluator/目标标签/截图。逐项skip清单在 `inventory-local.json`，没有造目标或替代评分。
3. IN3接口需要原 `hbx/Mistral-Interact` 权重服务，本次未部署。CAPTURE原训练组件仍缺，显式拒绝用普通prompt冒充。
4. STITCH轻量适配版与 `stitch_official` 分开命名。官方流水线已有独立通过记录；官方STITCH+REVOIR组合入口已接入，但本次实际验证的组合是轻量STITCH+REVOIR，不能混淆两者。
5. MemPA完整长期probe评分、Pi AppWorld任务、所有方法在所有来源上的完整交叉矩阵尚未运行。评分入口已接入，但未运行不能表述为复现完成。
   运维核查进一步确认：MemPA完整时间线不是连续1–108；当前adapter仅支持acc-range，尚需接通原acc-list/计划与probe流程。旧README的全量配置指引已更正，完整长期实验列为阻塞项，不能只改score=true即视为可执行。
6. Python/HTTP/进程接口是协作式公开数据边界，不是操作系统安全沙箱。面对不可信harness，应在独立容器中仅挂载workspace并从网络端提供事件，不能给它主机源码/私有任务路径访问权。

## 失败尝试与复现

所有失败目录保留在 `.local`，自动报告列出失败原因。早期 `mempa-native-v4` 虽原CLI退出0，但MCP工具启动存在兼容错误，应排除；以 `mempa-native-v7` 和 `mempa-direct` 为有效工具兼容试跑。旧 Pi 无 checklist 的 task001 不用于完成率比较。不能从调试中挑选最高得分当正式成绩。

STITCH v1–v6的依赖、入口兼容和输出字段问题均保留为失败尝试，v7为首次完整通过；详细差异见 `modify.md`。`run-records.json` 的 `eligible_for_smoke_claims` 只标记有效联调记录，不表示正式实验统计可用。

正式pilot应固定来源任务清单、代码散列、模型版本、原环境预算和规划预算后重新一次性运行。当前样本仅证明接入与识别工程错误；不支持显著性、泛化或方法优势结论。新运行manifest记录配置、来源提交和NovOurs代码散列；`.local`不上传凭据和完整私有运行轨迹。
