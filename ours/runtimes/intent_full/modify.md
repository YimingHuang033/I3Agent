# 2026-11-03 新增策略覆盖全集

为保留已完成讨论实验的冻结代码，新建intent_full_runtime，本地对应runtimes/intent_full。

- run_local.py、protocol.py、judge_audit.py、manage_services.py与讨论实验字节一致；模型、提示词、规则、top2纠正优先、max_tokens=768、temperature=0、seed=42、8并发均不变，服务继续使用8030/8031，仅目录隔离。
- prepare_full.py核验旧manifest的所有文件、模型/采样配置、discussion为full子集及192条任务身份。复制完整记录（含错误），保存源/目标SHA256；新manifest仅更新runtime路径和subset=full。不改写旧manifest，不把discussion进度冒充full进度。
- monitor.py将campaign改为full-20261103-v1，--subset改为full，模型总时限由90分钟调整到24小时，judge由30分钟调整到4小时；每模型分别检测15分钟无进度。仅在两模型全集完成后汇总，避免恢复过程重复读取全量轨迹。
- report.py选择full任务ID，对照原两组全集；保持主要指标定义，结果依旧是受控合成任务成绩，不是原生benchmark评测。
- 独立systemd服务立即启动，失败等待60秒后续跑，48小时最多4次启动。失败episode不删除、不美化；复用讨论子集5个模型错误。端口/GPU占用时拒绝接管其他作业。
- 全集42240次episode，其中192次经验证复用、42048次待新执行。结束后单步骤可见性裁判约5%，自动输出汇总。无训练，无包安装，无上游修改。
