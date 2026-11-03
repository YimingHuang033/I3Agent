# MemPABench / ProAgentBench 的 Ours 适配

远端根目录：`/home/tim/Proj/I3Agent`。本地 `ours/runtimes/mempa_proagent/` 部署为`ours2_runtime`，不改变已完成的Pi/Life代码与结果。

- `MemPABench/`：官方Git仓库；固定personas数据在`MemPABench-personas/`。
- `ProAgentBench/`：Hugging Face公开数据集的稀疏Git clone，固定revision；事件文本实体在`ProAgentBench-events/`。论文匿名评测代码当前403，不冒称已获取原评测代码。
- `mempabench_ours1/ours1/EXPERIMENT.md`、`proagentbench_ours1/ours1/EXPERIMENT.md`：来源、合成覆盖条件、配置、实际结果；根目录`modify.md`记改造。
- `campaigns/smoke-20261102-v1/`：两模型各32 episode的小规模验证。
- `campaigns/source-adapted-20261102-v1/`：全集；每模型11904，合计23808模型episode。与smoke是不同campaign；每个campaign内部只执行每个组合一次。

MemPA使用112个原生probe/cell，ProAgent使用17人各8个历史事件上下文。分别2688/3264条任务；四条件、两方向、三档干扰。明确历史/纠正和候选选择是新增控制协议，原生长程行为实现与When/How、图像、AppWorld均未执行。原版成绩不能与本实验直接比较。

Qwen3-8B与gpt-oss-20b各一张4090，B0当前会话/B1历史top2检索。沿用tim/lifesim-venv，不安装包。DeepSeek Flash改为单步骤可见信息审核，避免给裁判未来轨迹；仍只是补充审核。

## 运行与监控

```bash
cd /home/tim/Proj/I3Agent
python3 ours2_runtime/monitor.py status --campaign source-adapted-20261102-v1
python3 ours2_runtime/monitor.py stop --campaign source-adapted-20261102-v1
```

全量monitor每20分钟记录一次、10秒检测退出/进度，连接层最多2次重试；基础设施退出后有限次数重启服务、逐episode续跑。模型非法动作不自动修复或重试；结束后释放GPU、做约5%语义抽查并自动生成分项目结果。没有聊天自动唤醒功能。完整结果会更新EXPERIMENT.md；历史campaign报告保留在其results子目录。

## 复现与校验

- `prepare.py`：从固定来源生成数据，拒绝覆盖；原代码/数据保留不动。
- `check.py`：全5952任务三阶段金标准轨迹、U0/U1可见等价性、source哈希。
- `run_local.py` / `protocol.py`：冻结输入、私有oracle、原子checkpoint、无效动作计分。
- `manage_services.py` / `monitor.py`：本轮服务和进度；两runtime不能同时占用同一模型端口。
- `judge_audit.py`：每个检查点的当前可见信息，逐条落盘。
- `analyze.py`：离线实际轨迹汇总，不调用模型。
- `download_data.py`：本地公开事件文本下载与LFS SHA256校验；不是运行依赖。

未做训练。MemPA仅4个源用户、ProAgent17个参与者，变体不算独立人群；单次测试不能建立广泛能力结论。此前裁判已暴露语义可靠性问题，新裁判只验证接口与输入隔离，不声称已达到人工准确度。
