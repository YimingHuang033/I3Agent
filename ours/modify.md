# 2026-11-03 目录归并

所有Ours代码、设计、报告和专属历史快照归入ours。本地运行副本放runtimes、结果放reports；远端四个隔离项目和四组runtime放在ours下保持同级关系。原始来源移入benchmarks，旧绝对路径保留相对符号链接。

旧run_local.py/protocol.py/模型配置/输入/轨迹不变。新增tools/legacy_monitor.py仅适配迁移后的历史monitor启动路径，并维持有限恢复时的兼容入口；不改变模型输入或评分。project.py继续兼容旧路径。唯一调整的既有本地业务脚本为mempa_proagent/download_data.py：工作区根从parents[2]改为parents[3]，来源/输出改为benchmarks/sources和benchmarks/data；不运行下载器、不部署覆盖冻结远端代码。

文档更新相对链接和统一入口；原始仓库README、许可证、Git元数据不改。模型、tim和其他Python环境、凭据保持原位。数据移动使用同文件系统rename，不删除实验，不重新执行模型。10份冻结manifest与对应输入在迁移前后校验一致；详细清单见根目录archive/layout-20261103。

已完成的临时systemd服务可能在daemon-reload后被回收，因此为两个诊断campaign保存同名的持久服务定义并指向兼容启动器；未enable、未启动，没有新定时任务。只保留将来显式续跑能力。
