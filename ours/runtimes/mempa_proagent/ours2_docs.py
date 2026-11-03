from pathlib import Path
import json
R=Path('/home/tim/Proj/I3Agent');RT=R/'ours2_runtime';prep=json.loads((RT/'preparation.json').read_text())
for name in ['mempabench_ours1','proagentbench_ours1']:
 root=R/name;o=root/'ours1';counts=prep[name];is_mem=name.startswith('mempa')
 source='https://github.com/mempabench/mempabench' if is_mem else 'https://huggingface.co/datasets/qv9n2xk7m1z8pt4/ProAgentBench'
 specifics='''来源为官方代码commit 45dea874cc5cf9dad4bec5646cd2456eaab5bc3a，以及代码固定的数据revision 6d5fb9b2785bc9fb00c3e2c09920742043cd5a4f。4用户×14属性×2场景，共112个原生final probe，保留原任务背景、原属性setting定义及初始偏好。20个发生变化的cell使用原evolving_map的前后setting；其余cell的另一setting由确定性规则选取，是新增反事实。每个cell只选两档，不覆盖原属性所有setting。

原版通过99次交互逐渐暴露隐含习惯、模拟用户会反馈；本实验改成显式历史偏好与固定纠正，省略原工具执行和自由用户模型。因此本实验不是原版on-policy长程运行，不报告PSA/CS/PET/BRS原榜单分数。direction=1是反向反事实；即使使用原生change pair，后续纠正时点仍是新增协议。''' if is_mem else '''来源为论文链接的ProAgentBench公开数据仓库revision b5388f02dd99777af1d5ea473ccb3436276e7c05，使用17名参与者的event JSON。按每人事件时间顺序等距选8个事件，共136个上下文，只保留该事件摘要与至多3个过去摘要；不按is_llm_event或未来事件挑样，不向actor提供标签、截图路径或未来信息。

偏好并非此数据的原始标签：新增4类二选一交互策略（详略、介入、任务范围、行动确认）的显式历史与纠正；真值来自这些合成覆盖条件，不从模型生成摘要猜用户偏好。事件摘要也是发布方模型注释，不能当行为真值。原版论文匿名代码仓库当前403不可访问，本目录是公开数据集的Git clone及独立副本，不声称克隆了原版评测代码。当前文本模型没有加载截图，原版When/How多模态指标不在本次评测范围。'''
 design=f'''# {name}：来源、实验设计与结果

## 来源与改造边界

上游：[公开来源]({source})。

{specifics}

## 控制实验

{counts['templates']}个来源上下文/偏好cell × 2个方向 × 3种干扰历史长度（0/8/24）× 4条件（S保留、R修改、U0/U1歧义配对）= {counts['episodes']}条任务、{counts['pairs']}对。变体不算独立用户或真实任务。MemPA按用户D留出，ProAgent按参与者14–17留出；没有训练，先导/测试提示词调整不能使用这些保留组。实际小规模smoke只选每项目前两个来源的8条任务；全集按source cell/event覆盖的pilot优先，但每条只算一次。

三阶段：①新请求省略偏好；②明确持久纠正；③新会话再省略。每阶段最多一次澄清，脚本用户给已知偏好答案。U0/U1公开材料完全一致、隐藏目标相反。模型仅接收observation，私有oracle/source标签不进入请求。

B0只看当前会话；B1用已有CPU Qwen3-Embedding-0.6B检索top2用户历史。Qwen3-8B关闭thinking，gpt-oss-20b low reasoning，各用一张4090、8并发、temperature0、seed42、max_tokens768。动作是结构化候选选择，不实际发消息/操作应用。沿用既有tim/lifesim-venv，不安装新包、不训练。连接层最多2次自动重试，模型格式/动作错误不重试；逻辑请求数不是底层HTTP尝试数。

## 评分与裁判

主指标：三个阶段的最终正确率、首答直接正确、有效证据可见率、每任务问题数、断言覆盖率与规则unsupported计数。错误/弃权不移除。B0可通过重新提问得到高最终分，因此必须分开首答与澄清后准确率。规则unsupported依赖私有目标与引用一致性，不等同语义幻觉。

DeepSeek Flash抽查约5%轨迹，每阶段只看首次动作对应的单条可见observation和当前response，不提供其他阶段或未来响应；修正上一轮完整轨迹裁判的跨会话混淆。malformed actor响应仍由规则记失败，裁判跳过但不替换评分。裁判只作补充，格式验证通过不等于语义正确。

## 复现与限制

共享代码：../ours2_runtime（相对项目根目录）；原版Pi/Life与ours1_runtime保持不变。本项目source snapshot哈希在SOURCE_SNAPSHOT.json，完整provenance在private/templates.json与oracle.source。每参与者/属性的相关样本不能当独立IID样本；仅一轮、仅2基线，不作广泛模型排名。

离线检查：`lifesim-venv/bin/python ours2_runtime/check.py`。启动：`python3 ours2_runtime/monitor.py run --campaign source-adapted-20261102-v1 --subset full`。监控每20分钟记录状态、有限次数自动恢复，PID与status位于runtime。当前未跑原生benchmark全流程。

<!-- RESULTS -->

尚未开始模型测试；实际结果会由analyze.py读取轨迹后更新，不能用静态通过代替模型完成。
'''
 (o/'EXPERIMENT.md').write_text(design)
 (o/'README.md').write_text(f'# {name}\n\n[设计与结果](EXPERIMENT.md)；[修改记录](../modify.md)。共享运行代码与监控在../../ours2_runtime。来源与gold分离，数据是来源关联的合成改造，不是原版榜单任务。\n')
 (root/'modify.md').write_text(f'''# {name} 修改记录

上游来源：{source}；独立复制当前checkout的tracked文件，文件清单和SHA256在SOURCE_SNAPSHOT.json；没有修改上游clone。可选submodule源码留在上游，不在此副本展开；ProAgent图像/数据库LFS对象未下载，保留元数据/指针。来源数据通过固定revision与LFS SHA256校验，选择策略见ours1/EXPERIMENT.md。

新增ours1/data/public、data/private、configs、EXPERIMENT.md和README.md；共享新建ours2_runtime，未编辑既有Pi/Life/ours1_runtime实现或评分。新增prepare.py从来源probe/event生成固定配对，协议/actor/service/monitor来自已验证的ours1副本，并改为新项目路径/独立campaign。run_local仅将连接重试设为2并纳入manifest，提示词/评分逻辑与原控制器保持一致。judge_audit改为单步骤可见信息审核，防止看到未来/跨会话内容；评分仍以已知目标为主。check.py验证配对可见等价性、全部金标准轨迹、source哈希。analyze.py生成分项目实际结果，不调用模型。

{specifics}

资源沿用既有模型/embedding/DeepSeek凭据；不修改tim环境。任务规模：{counts['episodes']}，每模型×2基线={counts['episodes']*2}次episode。所有后续实际启动、失败、验收与结果补充在此记录。
''')
print('design and change records written')
