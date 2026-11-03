# pi_bench_ours1 修改记录

原始来源目录与独立源码副本均保持不变。`SOURCE_SNAPSHOT.json`记录逐文件哈希；运行前再次验证。与原版不同的文件均限于新增ours1侧目录；完整早期差异和校准记录保留于 [历史记录](docs/history/modify-20261102.md)，原部署差异见 upstream-deployment-notes.md。

## 2026-11-02 整理与持续实验

1. 将重复的模型驱动和控制器合并到 `../ours1_runtime/run_local.py` 与 `protocol.py`；原ours1/scripts入口改成兼容转发，原benchmark入口未改。保留数据/生成器/配置，未删除或覆盖实验日志。
2. 文档收敛到项目根README、共享运行README、一页实验设计；旧README、接口说明、设计副本和完整修改记录归档到ours1/archive/20261102-before-cleanup。共享临时校准脚本归档到runtime/archive/20261102-calibration。
3. 根据用户“持续运行ours中的实验并监控”的授权，将execution_enabled/full_execution_enabled设为true；training_enabled仍为false。使用既有tim包，不安装/升级；Qwen3-8B和gpt-oss-20b各一张4090，8并发，模型参数和动作协议沿用校准设置。
4. 驱动增加discussion/pilot/full子集、先导优先排序、逐episode原子保存、进程锁、代码/配置/数据哈希锁定、身份校验和断点续跑。已完成的成功或失败episode都不重复运行；中断时未完整保存的episode可能重做。结果写campaigns，不能混用改变后的配置。
5. 每次最多8条在途；模型非法输出记失败继续，网络/API基础设施异常完成当前批后熔断。STOP文件可停止；不自动猜测/修复模型答案，不训练，不在运行中修改提示词。
6. 新增monitor.py常驻进程：首次立即启动，20分钟记录一次快照，10秒检测退出/进度；15分钟无新checkpoint暂停。独占监控锁、PID登记，避免重复队列；全集一次完成后停止自身GPU服务，保留监控，不无限重复已完成实验。此环境无notify_on_output，因此这是远端监控，不声称自动唤醒聊天agent。
7. 裁判在actor全集完成后对哈希固定选择的约5%轨迹做DeepSeek Flash非thinking审核（4并发），包括模型错误，逐条存档；续跑保留已有裁判成功和失败，不无限重试消耗API。主指标仍是确定性目标评分。
8. check.py验证全部2304条三阶段协议、B0历史隔离、无效动作拒绝且不改变状态、消息时间顺序、原子保存/断点身份、源码哈希。报告保存在共享check-report.json。

当前状态/完整参数/停止和恢复命令：[共享说明](../../runtimes/pi_lifesim/README.md)。历史上“未运行/全集关闭”的文字仅描述当时阶段，不再代表当前授权。

## 方法边界

这仍是合成候选选择实验：脚本用户、私有oracle、B0当前会话与B1检索历史，非原NanoBot/LifeSim工具执行。每个项目32模板×72变体=2304episode，变体不能当独立模板。三个检查点最多六次请求。既有unsupported_claim_count衡量金标准与有效引用一致性，不完全等同于可见依据幻觉；空claims不能视为推断成功，应结合正确动作、提问负担和断言覆盖率。正式模型对比需模板级/配对分析与人工审核。冻结本轮设计，不因先导结果临时调整后继续混算。

验收：全部任务离线检查通过，原始源码及快照哈希一致；重复monitor启动被独占锁拒绝。campaign=full-20261102-v1，monitor PID=2016347，首次定时检查2026-11-02 02:15:11 +08:00。复现归档reproducibility.tar.gz仅约498KB，不含凭据。本地旧Ours临时目录已压缩归档并逐文件校验后移出活动目录，当前本地代码仅ours1/。tim包与安装历史再次核对未变。

## 2026-11-02 上午：恢复意外暂停

02:01 Qwen单次APIConnectionError触发保护停机；旧monitor此后只定时记录blocked，未自动恢复。上午人工检查后修正monitor.py：仅对基础设施退出码2加入30秒后重启/断点续跑；连续不足128条进展最多3次，campaign累计最多24次，recovery.json记录次数。未知故障仍停止。status增加worker_alive，避免把上次progress中的running误当存活。actor代码、模型/提示词/数据/评分与manifest完全未改，已有错误也保留，不自动重做。服务日志无崩溃/OOM记录，具体断连原因未确定。本次恢复是检查后进行，并非此前监控自动完成。

## 2026-11-02 全集离线汇总

新增ours1/EXPERIMENT.md，将实验设计、动作/提问/断言指标、按条件/模板划分/历史长度的结果、配对统计、错误与限制写在同一文档。新增ours1/results/full-20261102-v1/summary.json。共享新增analyze.py，直接读取18432条轨迹重新计算并校验完整性、runner计数与冻结哈希；不修改原始分数，不补跑模型/裁判。B1−B0差值用模板簇2000次bootstrap（seed42）提供探索性95%区间，不将改写当独立模板。发现裁判多余提问判断不可靠，原始判定保留但不用于主结论；全局汇总见runtime/campaigns/full-20261102-v1/RESULTS.md。

## 2026-11-02 项目目录整理

仅整理项目根目录的文档与非运行部署材料，新增只读project.py状态入口。当前项目、原始来源、runtime代码/数据/campaign/模型/环境/凭据均保持原路径，冻结manifest哈希与源文件快照重新校验通过。历史安装包/一次性setup脚本移入../archive/layout-20261102，原路径及SHA256在moves.json；原安装需要时按清单恢复路径。详见../docs/directory-layout.md。未重跑任务或修改评分。


## 2026-11-03 统一收纳

项目实际目录移入I3Agent/ours，原始来源移入benchmarks/sources，旧绝对路径保留兼容链接。模型代码、数据、评分和历史结果未改变；详情见../modify.md及../../docs/project/directory-layout.md。历史冻结monitor续跑使用../tools/legacy_monitor.py。
