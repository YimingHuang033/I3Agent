# 意图推断讨论子集：今晚诊断运行

北京时间2026-11-02 23:30开始，运行48条已有讨论任务的full-history和显式纠正优先策略，Qwen3-8B/gpt-oss-20b合计192次新episode。未增加合成任务，也未训练模型。沿用四个来源任务与私有oracle，旧B0/B1从原结果读取。

部署：`/home/tim/Proj/I3Agent/intent_diagnostics_runtime`。结果：`campaigns/discussion-20261102-v1/RESULTS.md`，详细指标`analysis.json`，状态`status.json`。预估启动、模型推理、抽查共15–40分钟，属于估计；异常会保留日志并标记blocked，不保证全部模型输出正确。

```bash
python3 project.py status intent-diagnostics
ssh BBQCard2 'systemctl --user status i3agent-intent-discussion-20261102.timer'
# 取消尚未开始的定时任务：
ssh BBQCard2 'systemctl --user stop i3agent-intent-discussion-20261102.timer'
# 停止已启动的任务：
ssh BBQCard2 'systemctl --user stop i3agent-intent-discussion-20261102.service'
```

[修改与方法限制](modify.md)。人工讨论仍聚焦少量任务的配对合理性和评分依据；自动运行不能替代人工审核。
