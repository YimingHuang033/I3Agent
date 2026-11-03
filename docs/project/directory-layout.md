# 目录维护说明（2026-11-03）

根目录仅保留入口、状态工具及四类内容：ours、benchmarks、docs、archive（远端另有模型、环境及凭据）。

## 收纳规则

- Ours代码、设计、结果、旧快照统一进入ours；各阶段历史结果独立保存，避免合并覆盖或破坏来源关系。
- 原始仓库统一进入benchmarks/sources，配套原数据进入benchmarks/data，原版运行介绍进入benchmarks/docs。
- 研究草案、图片、PDF、导出件与来源核查材料统一进入docs/research；目录说明归入docs/project。
- 通用临时材料与迁移清单保留archive。上次迁移的清单是历史记录，不替换其中原始路径；按日期串联迁移记录。

## 本地与远端

本地ours/runtimes是代码工作副本、ours/reports是报告副本；服务器ours保留四个隔离项目及各runtime同级布局，完整轨迹仍在对应runtime/campaigns。

服务器原路径保留相对符号链接，实际文件已迁移，无重复拷贝。链接用于旧绝对路径、Git来源路径、源码快照记录与环境兼容；不能删除后期待历史配置继续工作。模型、Python环境和deepseek.env.sh未迁移，避免破坏安装路径或凭据权限。

Python的Path.resolve会穿透符号链接；因此仅有链接不足以保证旧monitor恢复时生成相同的manifest路径键。ours/tools/legacy_monitor.py在导入原monitor后还原原ROOT/PROJECT/CAMPAIGN路径，再进入原main；原run_local.py、protocol.py与旧manifest均不改写。两个诊断systemd服务使用此兼容入口。只读project.py不依赖此恢复机制。

## 本次验证

迁移前后10份模型manifest及其输入文件SHA256保持一致。原版源码与隔离快照按SOURCE_SNAPSHOT校验。文档相对链接、源仓库Git状态和只读状态入口复核。迁移记录位于archive/layout-20261103；未重跑任务、训练模型或改变评分。

同类说明通过总入口聚合，不把不同实验配置强行合并。没有发现当前维护范围内字节完全相同的Markdown，因此未删除看似相似但有不同实验含义的文档。
