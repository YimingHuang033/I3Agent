# proagentbench_ours1 修改记录

上游来源：https://huggingface.co/datasets/qv9n2xk7m1z8pt4/ProAgentBench；独立复制当前checkout的tracked文件，文件清单和SHA256在SOURCE_SNAPSHOT.json；没有修改上游clone。可选submodule源码留在上游，不在此副本展开；ProAgent图像/数据库LFS对象未下载，保留元数据/指针。来源数据通过固定revision与LFS SHA256校验，选择策略见ours1/EXPERIMENT.md。

新增ours1/data/public、data/private、configs、EXPERIMENT.md和README.md；共享新建ours2_runtime，未编辑既有Pi/Life/ours1_runtime实现或评分。新增prepare.py从来源probe/event生成固定配对，协议/actor/service/monitor来自已验证的ours1副本，并改为新项目路径/独立campaign。run_local仅将连接重试设为2并纳入manifest，提示词/评分逻辑与原控制器保持一致。judge_audit改为单步骤可见信息审核，防止看到未来/跨会话内容；评分仍以已知目标为主。check.py验证配对可见等价性、全部金标准轨迹、source哈希。analyze.py生成分项目实际结果，不调用模型。

来源为论文链接的ProAgentBench公开数据仓库revision b5388f02dd99777af1d5ea473ccb3436276e7c05，使用17名参与者的event JSON。按每人事件时间顺序等距选8个事件，共136个上下文，只保留该事件摘要与至多3个过去摘要；不按is_llm_event或未来事件挑样，不向actor提供标签、截图路径或未来信息。

偏好并非此数据的原始标签：新增4类二选一交互策略（详略、介入、任务范围、行动确认）的显式历史与纠正；真值来自这些合成覆盖条件，不从模型生成摘要猜用户偏好。事件摘要也是发布方模型注释，不能当行为真值。原版论文匿名代码仓库当前403不可访问，本目录是公开数据集的Git clone及独立副本，不声称克隆了原版评测代码。当前文本模型没有加载截图，原版When/How多模态指标不在本次评测范围。

资源沿用既有模型/embedding/DeepSeek凭据；不修改tim环境。任务规模：3264，每模型×2基线=6528次episode。所有后续实际启动、失败、验收与结果补充在此记录。

实测验收（2026-11-02）：全5952条任务离线验证通过。smoke两模型各32条完成，Qwen无错误、gpt-oss3条协议错误，无基础设施错误；裁判6条轨迹18步骤接口成功。汇总脚本初版拼接缺换行已修正并通过全文件语法检查，smoke结果已生成。全量campaign source-adapted-20261102-v1已启动，模型总数23808，完成后自动离线更新EXPERIMENT.md。上游ProAgent匿名代码403、截图未下载；MemPA附带的可选MemOS/mem0原生memory后端未用于本适配，本地递归clone已完成，远端递归获取仍在后台。

## 2026-11-02 项目目录整理

仅整理项目根目录的文档与非运行部署材料，新增只读project.py状态入口。当前项目、原始来源、runtime代码/数据/campaign/模型/环境/凭据均保持原路径，冻结manifest哈希与源文件快照重新校验通过。历史安装包/一次性setup脚本移入../archive/layout-20261102，原路径及SHA256在moves.json；原安装需要时按清单恢复路径。详见../docs/directory-layout.md。未重跑任务或修改评分。


## 2026-11-03 统一收纳

项目实际目录移入I3Agent/ours，原始来源移入benchmarks/sources，旧绝对路径保留兼容链接。模型代码、数据、评分和历史结果未改变；详情见../modify.md及../../docs/project/directory-layout.md。历史冻结monitor续跑使用../tools/legacy_monitor.py。
