# 2026-11-02 今晚诊断任务的改动

独立本地目录`runtimes/intent_diagnostics`部署到BBQCard2的`intent_diagnostics_runtime`。不修改四个上游benchmark、旧Ours协议、任务或冻结campaign。

- `run_local.py`复制自Pi/Life运行器，仅把两种策略改为`full_history`与`correction_priority`，SDK传输重试由0改为2；模型输出非法不重试，仍记错误。提示词、模型参数、每检查点一次提问、规则计分均沿用。
- `protocol.py`保留原控制器/评分；full_history按时间展示全部过去用户记录；correction_priority先做原embedding top2检索，若历史文本命中显式持久纠正规则，就把最新命中记录置入有限的两个位置，再按时间展示。规则为“从现在起”“以后…默认/按”“默认…改为/改成/替换”“更改默认偏好”“旧的…不再有效”。不读oracle、条件、证据ID或未来消息。该启发式只用于当前显式中文纠正诊断，不声称泛化的意图状态管理。full-history是更多上下文的参照，不是等输入token预算对照。
- `manage_services.py`沿用已有vLLM配置，独立PID/日志目录及8030/8031端口；GPU0/1、模型权重、tim与lifesim-venv依赖不变，不安装包。
- `judge_audit.py`复制MemPA/ProAgent的单检查点可见性审核；约5%抽查，无人工准确度保证。
- `monitor.py`为一次性任务：GPU被占则拒绝接管；模型启动上限10分钟、无进度15分钟停止、模型阶段90分钟上限、裁判30分钟上限。每10秒更新状态，每20分钟记监控快照，完成退出；保留checkpoint。网络SDK最多2次重试；不自动掩盖模型错误或无限重启。收到STOP/终止信号只清理本任务启动的服务。
- `report.py`仅复用旧全集中相同讨论任务ID的B0/B1，与新增两策略并列汇总。48条任务×2新增策略×2模型=192次新episode，最多1152次助手响应。旧轨迹不重跑、不重写；保存来源哈希。报告只是探索性分组统计，不作显著性结论。
- 定时：北京时间2026-11-02 23:30，由服务器用户级systemd一次性timer触发，退出本地SSH不影响；服务器关机将影响执行。禁止训练。小组讨论与人工评分审核仍待进行。
