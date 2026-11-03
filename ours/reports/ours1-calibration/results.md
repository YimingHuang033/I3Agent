# Ours1本地模型校准

## 实测结果与效率外推（2026-11-02）
设备：双RTX4090，每模型各一张；Qwen3-8B关闭thinking，gpt-oss-20b low reasoning。每个档位每模型32个episode，两个基线各16个。以下时间不含预热；一次测量，非置信区间。

### serial
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-013619-serial`
- Qwen3-8B: 160.89s / 32 episodes，11.93 episodes/min；协议正常 32/32，请求 144，p50/p95 1.239/1.313s；端到端输出 53.6 tokens/s，截断 0。CPU embedding编码累计 10.73s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 60，规则不支持断言 16。
- gpt-oss-20b: 90.84s / 32 episodes，21.14 episodes/min；协议正常 24/32，请求 136，p50/p95 0.443/1.401s；端到端输出 165.5 tokens/s，截断 0。CPU embedding编码累计 10.80s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 9, 16]/16；澄清 32 次，断言 20，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 11, 12]/16；澄清 8 次，断言 21，规则不支持断言 1。

### parallel4
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-013910-parallel4`
- Qwen3-8B: 45.88s / 32 episodes，41.85 episodes/min；协议正常 32/32，请求 144，p50/p95 1.322/1.403s；端到端输出 188.0 tokens/s，截断 0。CPU embedding编码累计 11.52s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 55，规则不支持断言 9。
- gpt-oss-20b: 33.53s / 32 episodes，57.26 episodes/min；协议正常 27/32，请求 136，p50/p95 0.669/1.639s；端到端输出 387.4 tokens/s，截断 0。CPU embedding编码累计 11.21s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 10, 16]/16；澄清 32 次，断言 19，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 13, 12]/16；澄清 8 次，断言 22，规则不支持断言 3。

### parallel8
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-014005-parallel8`
- Qwen3-8B: 27.80s / 32 episodes，69.05 episodes/min；协议正常 32/32，请求 144，p50/p95 1.341/1.428s；端到端输出 310.2 tokens/s，截断 0。CPU embedding编码累计 12.02s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 56，规则不支持断言 10。
- gpt-oss-20b: 25.07s / 32 episodes，76.58 episodes/min；协议正常 25/32，请求 136，p50/p95 0.766/2.030s；端到端输出 557.1 tokens/s，截断 0。CPU embedding编码累计 12.43s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 10, 16]/16；澄清 32 次，断言 14，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 13, 12]/16；澄清 8 次，断言 27，规则不支持断言 4。

### DeepSeek Flash补充裁判
8/8 成功，4并发耗时 2.86s，prompt/completion tokens=14974/765。输出 `../ours1_runtime/judge-audit-final/`。抽样按模型×项目×基线覆盖8格，包括协议失败案例，不按成功筛掉困难样本。仅将公开轨迹发送云端。

### 全集耗时估计
全集4608个episode×2基线×2模型=18432次模型episode；每模型9216次。两卡同时运行，以较慢模型结束时间为准。
- 按serial实测吞吐线性外推：两卡约 12.87 小时（仅本地actor阶段）。
- 按parallel4实测吞吐线性外推：两卡约 3.67 小时（仅本地actor阶段）。
- 按parallel8实测吞吐线性外推：两卡约 2.22 小时（仅本地actor阶段）。
考虑64模板的新文本、较少缓存复用、输出长度和CPU检索差异，以8并发估计预留 3.3–6.7 小时；这是预算余量而非统计区间。先导256个episode×两基线×两模型=1024次模型episode，理想用时为全集的1/18，另加启动/预热。
若每个模型episode都做一次同等长度judge审核，按本次4并发样本粗推另需约1.83小时（串行阶段相加；流水线可重叠）。该推算仅8例，不能代表长期速率、费用或限流。确定性行动评分覆盖全部即可，语义审核可先抽5–10%并检查争议例。

### 验收与保留限制
- tim环境323个包版本和conda安装历史哈希均未改变；两个来源项目和快照的15584/64个源码文件均与原manifest一致。
- 未启动全集、训练或原生工具执行；执行开关仍禁止全集。所有初始失败日志与模型非法动作保留。
- 首次服务启动至ready约44s（Qwen）/53s（gpt-oss）；gpt-oss首次请求约41s，后续显著缩短，已计入单独warmup。首次编译缓存与已有缓存有关，不能保证未来冷启动耗时相同。

## 收尾与裁判配置修正

- DeepSeek初轮未显式关闭thinking，1024 token上限造成5/8响应截断，保留于 ours1_runtime/judge-audit/。最终显式设置thinking.type=disabled，仍使用1024上限，8/8成功，4并发2.86s；输出token共765。参考官方参数文档：https://api-docs.deepseek.com/guides/thinking_mode/ 。未安装新SDK。关闭thinking会改变裁判模式，本轮只验证接口和吞吐，正式实验应固定并验证裁判设置。
- 最终judge脚本也保留协议错误的原始模型输出供审核，不能用成功样本筛选掩盖模型错误。
- 三档gpt-oss错误分别8/32、5/32、7/32，均为Invalid commit，未观察到HTTP超时或token截断；Qwen三档均32/32协议正常。并发批处理下即使temperature=0/seed=42也不能据此保证完全一致，正式结论需要重复与模板级统计。
- 结果汇总保存于 ../ours1_runtime/calibration-report.json 与 calibration-results.md；新增 collect_results.py 汇总脚本和 update_docs.py 文档脚本，所有差异仅位于ours1侧与共享runtime。
- 已停止本轮两个vLLM服务，释放GPU；未改变其他用户服务。重启使用上述manage_services.py start。
