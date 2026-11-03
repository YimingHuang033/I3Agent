# Ours实验

[一页实验设计](docs/experiment-design.md) · [新增策略全集总结](reports/intent-full/SUMMARY.md) · [完整分组结果](reports/intent-full/RESULTS.md)

## 本地目录

- `runtimes/pi_lifesim/`：Pi/Life两基线实现；[说明](runtimes/pi_lifesim/README.md)。
- `runtimes/mempa_proagent/`：MemPA/ProAgent来源适配；[说明](runtimes/mempa_proagent/README.md)。
- `runtimes/intent_diagnostics/`：新增策略讨论子集；[说明](runtimes/intent_diagnostics/README.md)。
- `runtimes/intent_full/`：新增策略全集；[说明](runtimes/intent_full/README.md)。
- `reports/`：上述实验的报告副本；`ours1-calibration`保留先导历史，`ours1-full`、`ours2`、`intent-full`分别收纳各阶段结果。
- `docs/`：研究设计；`tools/`：历史路径兼容启动器；`archive/`：Ours历史快照。

原始benchmark统一放在[benchmarks](../benchmarks/README.md)，不在本地再次复制。四个Ours新增实验层收录在`projects/`，完整原始源码由benchmark submodule提供；完整运行轨迹保存在远端。

## 远端布局

实际目录已统一在`/home/tim/Proj/I3Agent/ours/`：四个`*_ours1`项目与`ours1_runtime`、`ours2_runtime`、`intent_diagnostics_runtime`、`intent_full_runtime`作为同级目录。保持同级关系是为兼容代码中的父目录定位，不把冻结代码重新合并。每个runtime内保留campaign、模型轨迹、日志和完整报告。

根目录旧路径是兼容链接，供绝对路径manifest和历史命令使用。已完成任务无需重新启动。若确需续跑冻结campaign，应使用`ours/tools/legacy_monitor.py`，它保留原路径拼写，不修改模型协议或manifest：

```bash
# 服务器上只读检查路径：
python3 ours/tools/legacy_monitor.py intent_full_runtime --inspect
# 需要恢复时才运行（使用原有checkpoint）：
python3 ours/tools/legacy_monitor.py intent_full_runtime
```

普通状态查看仍使用根目录`project.py`。本轮没有重跑模型或修改历史评分。目录迁移说明见[modify.md](modify.md)。

[Pi Ours](projects/pi_bench_ours1/ours1/EXPERIMENT.md) · [LifeSim Ours](projects/lifesim_ours1/ours1/EXPERIMENT.md) · [MemPA Ours](projects/mempabench_ours1/ours1/EXPERIMENT.md) · [ProAgent Ours](projects/proagentbench_ours1/ours1/EXPERIMENT.md)
