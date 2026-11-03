# mempabench_ours1 修改记录

上游来源：https://github.com/mempabench/mempabench；独立复制当前checkout的tracked文件，文件清单和SHA256在SOURCE_SNAPSHOT.json；没有修改上游clone。可选submodule源码留在上游，不在此副本展开；ProAgent图像/数据库LFS对象未下载，保留元数据/指针。来源数据通过固定revision与LFS SHA256校验，选择策略见ours1/EXPERIMENT.md。

新增ours1/data/public、data/private、configs、EXPERIMENT.md和README.md；共享新建ours2_runtime，未编辑既有Pi/Life/ours1_runtime实现或评分。新增prepare.py从来源probe/event生成固定配对，协议/actor/service/monitor来自已验证的ours1副本，并改为新项目路径/独立campaign。run_local仅将连接重试设为2并纳入manifest，提示词/评分逻辑与原控制器保持一致。judge_audit改为单步骤可见信息审核，防止看到未来/跨会话内容；评分仍以已知目标为主。check.py验证配对可见等价性、全部金标准轨迹、source哈希。analyze.py生成分项目实际结果，不调用模型。

来源为官方代码commit 45dea874cc5cf9dad4bec5646cd2456eaab5bc3a，以及代码固定的数据revision 6d5fb9b2785bc9fb00c3e2c09920742043cd5a4f。4用户×14属性×2场景，共112个原生final probe，保留原任务背景、原属性setting定义及初始偏好。20个发生变化的cell使用原evolving_map的前后setting；其余cell的另一setting由确定性规则选取，是新增反事实。每个cell只选两档，不覆盖原属性所有setting。

原版通过99次交互逐渐暴露隐含习惯、模拟用户会反馈；本实验改成显式历史偏好与固定纠正，省略原工具执行和自由用户模型。因此本实验不是原版on-policy长程运行，不报告PSA/CS/PET/BRS原榜单分数。direction=1是反向反事实；即使使用原生change pair，后续纠正时点仍是新增协议。

资源沿用既有模型/embedding/DeepSeek凭据；不修改tim环境。任务规模：2688，每模型×2基线=5376次episode。所有后续实际启动、失败、验收与结果补充在此记录。

实测验收（2026-11-02）：全5952条任务离线验证通过。smoke两模型各32条完成，Qwen无错误、gpt-oss3条协议错误，无基础设施错误；裁判6条轨迹18步骤接口成功。汇总脚本初版拼接缺换行已修正并通过全文件语法检查，smoke结果已生成。全量campaign source-adapted-20261102-v1已启动，模型总数23808，完成后自动离线更新EXPERIMENT.md。上游ProAgent匿名代码403、截图未下载；MemPA附带的可选MemOS/mem0原生memory后端未用于本适配，本地递归clone已完成，远端递归获取仍在后台。
