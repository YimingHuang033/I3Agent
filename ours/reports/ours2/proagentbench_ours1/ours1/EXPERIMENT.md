# proagentbench_ours1：来源、实验设计与结果

## 来源与改造边界

上游：[公开来源](https://huggingface.co/datasets/qv9n2xk7m1z8pt4/ProAgentBench)。

来源为论文链接的ProAgentBench公开数据仓库revision b5388f02dd99777af1d5ea473ccb3436276e7c05，使用17名参与者的event JSON。按每人事件时间顺序等距选8个事件，共136个上下文，只保留该事件摘要与至多3个过去摘要；不按is_llm_event或未来事件挑样，不向actor提供标签、截图路径或未来信息。

偏好并非此数据的原始标签：新增4类二选一交互策略（详略、介入、任务范围、行动确认）的显式历史与纠正；真值来自这些合成覆盖条件，不从模型生成摘要猜用户偏好。事件摘要也是发布方模型注释，不能当行为真值。原版论文匿名代码仓库当前403不可访问，本目录是公开数据集的Git clone及独立副本，不声称克隆了原版评测代码。当前文本模型没有加载截图，原版When/How多模态指标不在本次评测范围。

## 控制实验

136个来源上下文/偏好cell × 2个方向 × 3种干扰历史长度（0/8/24）× 4条件（S保留、R修改、U0/U1歧义配对）= 3264条任务、1632对。变体不算独立用户或真实任务。MemPA按用户D留出，ProAgent按参与者14–17留出；没有训练，先导/测试提示词调整不能使用这些保留组。实际小规模smoke只选每项目前两个来源的8条任务；全集按source cell/event覆盖的pilot优先，但每条只算一次。

三阶段：①新请求省略偏好；②明确持久纠正；③新会话再省略。每阶段最多一次澄清，脚本用户给已知偏好答案。U0/U1公开材料完全一致、隐藏目标相反。模型仅接收observation，私有oracle/source标签不进入请求。

B0只看当前会话；B1用已有CPU Qwen3-Embedding-0.6B检索top2用户历史。Qwen3-8B关闭thinking，gpt-oss-20b low reasoning，各用一张4090、8并发、temperature0、seed42、max_tokens768。动作是结构化候选选择，不实际发消息/操作应用。沿用既有tim/lifesim-venv，不安装新包、不训练。连接层最多2次自动重试，模型格式/动作错误不重试；逻辑请求数不是底层HTTP尝试数。

## 评分与裁判

主指标：三个阶段的最终正确率、首答直接正确、有效证据可见率、每任务问题数、断言覆盖率与规则unsupported计数。错误/弃权不移除。B0可通过重新提问得到高最终分，因此必须分开首答与澄清后准确率。规则unsupported依赖私有目标与引用一致性，不等同语义幻觉。

DeepSeek Flash抽查约5%轨迹，每阶段只看首次动作对应的单条可见observation和当前response，不提供其他阶段或未来响应；修正上一轮完整轨迹裁判的跨会话混淆。malformed actor响应仍由规则记失败，裁判跳过但不替换评分。裁判只作补充，格式验证通过不等于语义正确。

## 复现与限制

共享代码：../ours2_runtime（相对项目根目录）；原版Pi/Life与ours1_runtime保持不变。本项目source snapshot哈希在SOURCE_SNAPSHOT.json，完整provenance在private/templates.json与oracle.source。每参与者/属性的相关样本不能当独立IID样本；仅一轮、仅2基线，不作广泛模型排名。

离线检查：`lifesim-venv/bin/python ours2_runtime/check.py`。启动：`python3 ours2_runtime/monitor.py run --campaign source-adapted-20261102-v1 --subset full`。监控每20分钟记录状态、有限次数自动恢复，PID与status位于runtime。当前未跑原生benchmark全流程。

<!-- RESULTS -->

## 已执行结果
运行 `smoke-20261102-v1`；此表只汇总已保存的32次模型episode，不把尚未执行项目计为成功。
| 模型 | 基线 | 已执行 | 阶段0正确 | 阶段1正确 | 阶段2正确 | 问题/episode | 错误episode |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | current_session | 8 | 100.00% | 100.00% | 100.00% | 2.000 | 0 |
| Qwen3-8B | history_retrieval | 8 | 100.00% | 100.00% | 100.00% | 1.625 | 0 |
| gpt-oss-20b | current_session | 8 | 100.00% | 100.00% | 100.00% | 1.875 | 0 |
| gpt-oss-20b | history_retrieval | 8 | 100.00% | 62.50% | 87.50% | 1.250 | 2 |

阶段2允许澄清后的最终正确率不等同记忆保持。B0可重新询问脚本用户；B1的有效证据可见率、首答正确率及断言覆盖率详见JSON。无效输出和基础设施失败均保留，不能把协议完成当作做对。没有把本表称作原版PSA/PET/BRS或When/How成绩。
机器结果：`results/smoke-20261102-v1/summary.json`；全轨迹：`/home/tim/Proj/I3Agent/ours2_runtime/campaigns/smoke-20261102-v1/{qwen,gptoss}/episodes/`。

全量运行另见 ../../ours2_runtime/campaigns/source-adapted-20261102-v1/status.json；上表为独立smoke结果，不能作为全量结果。
