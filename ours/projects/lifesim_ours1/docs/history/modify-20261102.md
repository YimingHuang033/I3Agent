# lifesim_ours1 修改与准备记录

## 状态

当前更新：已授权并执行小规模本地 vLLM 校准；全量运行和训练仍关闭。以下“未运行”描述是最初静态准备阶段的历史记录，最新状态以本文件末尾为准。

2026-11-02：设计讨论与静态准备，未调用模型，未运行 benchmark / episode / embedding / 裁判，未训练。execution_enabled=false，training_enabled=false。

## 隔离方式与来源

- 来源：`/home/tim/Proj/I3Agent/lifesim`；保留原目录不变。
- 当前目录是独立文件副本，不是指向原目录的符号链接或硬链接；没有复制 .git、env.sh、.env、旧 outputs、向量库、虚拟环境。
- 来源文件与副本的逐文件 SHA256 在 SOURCE_SNAPSHOT.json。Pi-Bench 采用部署后的已跟踪代码及指定配置；LifeSim 没有原 .git，使用已部署的源码树，不能声称有可验证的完整 Git 克隆。
- 原部署记录另存 upstream-deployment-notes.md。原源码、模型适配与评分文件未作本轮修改。
- 原脚本仍是原 benchmark 的入口，不能直接跑 ours1。共享 Python 环境和 embedding 路径只写在配置中，未修改、未加载；凭据只记录仓库外 env 文件路径和环境变量名，未复制 Key。

## 本轮新增

- ours1/EXPERIMENT_DESIGN.md：一页讨论稿，两项目共享协议与指标口径。
- ours1/data/public/episodes.jsonl：2,304 个合成 episode，32 基础模板 × 2 方向 × 3 干扰历史长度 × 3 措辞 × 4 条件。
- ours1/data/private/oracle.jsonl、pairs.json、templates.json、subsets.json：私有目标、固定纠正脚本、1,152 个配对、模板族/保留组划分和讨论/先导/全集索引。正式运行须由控制器持有，actor 不得读取。
- ours1/generation/：可重复生成数据的纯标准库程序及可扩展模板清单，不调用模型。
- ours1/configs/：B0 当前会话、B1 embedding 检索历史的配置、响应契约、预算、执行关闭开关。
- ours1/scripts/protocol.py：模型无关的三检查点交互与计数接口；无模型 driver，未执行功能测试。
- ours1/scripts/prepare.py：静态 JSON/配对/语法检查并生成 preparation-report.json，不进行实验。
- ours1/README.md 与 HARNESS_INTERFACE.md：资源、现有框架接入位置、私有数据边界及待完成事项。

## 与原 benchmark 的方法差异

ours1 是借用原框架场景构造的合成偏好选择实验，不是官方新增任务集或排行榜结果。脚本式用户替代自由生成用户，以控制披露和纠正时点；逐检查点规则替代原总分用于主指标。动作目前为候选方案选择，不证明实际文件/工具执行。历史有效期和一次性例外留作下一阶段，不混入本轮主结论。

## 数量与分析边界

每个项目 32 个模板、2,304 个 episode；合计 64 模板、4,608 episode、2,304 配对。变体不能视为独立模板。默认讨论子集每项目16条，先导128条，全集2304条。未进行人工语义审阅或模型质量验证；不得用静态通过声称模型实验已跑通。

## 后续待讨论/实现

审核措辞与样例、确定先导/全集预算、实现并验证 native harness/model driver 和运行沙箱、协议功能测试与失败计分，再决定实际试跑。当前不提供 API 启动命令。

## 最终静态验收

- 源文件与独立快照 SHA256 全部匹配，原项目未改变。
- 全集每项目 2,304 条 / 1,152 对；配对等价性、唯一 ID、候选金标准合法性及 Python AST 检查通过。
- 在本地另外生成临时数据并逐文件哈希比对，生成器可复现当前数据；仅生成文件，没有执行 episode。
- 未加载 embedding、未调用模型或裁判、未运行协议功能测试、未训练。
- 后续 driver/harness 接线及人工语义审核仍待设计讨论，当前不声称一键模型实验可运行。

## 本地 vLLM 调试与效率测量（2026-11-02）

用户已授权实际模型调试；此前“仅准备”限制对小规模校准解除，训练和全量执行仍关闭。两套原 benchmark 目录不变。

- Qwen 暂用 /mnt/data/Qwen3-8B（目录存在多个 Qwen，本轮按已说明的默认选择使用8B）；另用 /mnt/data/gpt-oss-20b。每模型单独一张 4090，vLLM OpenAI API 仅监听 localhost 8020/8021。
- 新增 ours1/scripts/run_local.py：共享受控 JSON 决策 harness，复用控制器与两基线，不使用原 NanoBot / LifeSim 助手执行循环；测试结果属于 ours1，不是原榜单结果。
- 配置仅开启 calibration_authorized，小规模入口只接受每项目 4 或 8 条、并发 1/4/8；不能用此入口跑全集。明确授权开关、超时、零重试、协议错误记未完成均有记录。
- 响应结构约束通过 vLLM JSON schema；Qwen 关闭 thinking，gpt-oss low reasoning；max_tokens 默认 768，实际如需改动另记录。
- embedding 仍在 CPU，缓存仅文本向量，不跨 episode 共享偏好/对话状态；记录其耗时与首轮加载开销。
- 只将 observation() 的公开内容发送到模型 API。模型不获得文件系统/工具访问，因此 private oracle 不会进入被测输入。控制器和规则评分保持私有。
- 裁判使用已有 DeepSeek Flash Key（仓库外 env 文件），做补充语义抽查。主指标来自确定性目标，不用 judge 覆盖明确对错。
- 单独记录 warmup、稳定运行 wall time、每请求延迟、token用量、错误和截断；tokens/s 是端到端吞吐，不是纯 decode 速度。

## 本轮运行实现与环境保护

- 使用 conda tim 已安装的 vLLM/torch，不安装、升级、删除包；客户端使用继承该环境的既有 lifesim-venv。无须创建 tim2。运行前后保存并比较包版本清单与 conda-meta/history SHA256。
- FlashInfer sampler 首次启动因缺 nvcc 失败。通过服务进程环境变量 VLLM_USE_FLASHINFER_SAMPLER=0 使用替代采样实现，未安装 CUDA Toolkit 或改变 tim。gpt-oss 的注意力/量化内核仍由 vLLM 自动选择 TRITON_ATTN/MARLIN。
- 每卡独立服务，max_model_len=8192，max_num_seqs=16，max_num_batched_tokens=4096，gpu_memory_utilization=0.88，prefix caching 开启，CUDA graph capture sizes=[1,2,4,8,16]。这不是显存最小化配置；约20GB是服务预留量。
- 新增共享运行工具 ../ours1_runtime/manage_services.py、launch_batch.py、finish_calibration.py、judge_audit.py、run_local.py。manage_services 只停止 PID 与模型路径均匹配的本轮服务；finish_calibration 顺序执行并发档位，最后执行裁判抽查。
- scripts/protocol.py 修复消息时间戳：统一单调计数器，归档时保留原时间戳，新会话时间继续增加。原先助手时间戳可能比后续用户纠正大，造成顺序误导。timestamp-unit-checks.json 保存16案例×3检查点的通过记录。
- 首轮16 episode/模型仅用于冒烟检查，位于 runs/20261102-013235-serial，使用修复前时间戳。后续可比较测速统一每模型32 episode：2项目×8案例×2基线；每项目仅一个development模板、方向0、措辞0、历史干扰0/24和四个条件。未触碰heldout模板。
- gpt-oss 冒烟阶段出现 commit + option_id=null，保留为非法动作失败。结构化 JSON schema 保证基本字段形状，不保证动态候选ID/跨字段语义正确；controller 继续严格校验。不重试、不自动修正答案、不移除失败分母。
- 两个模型每档同时测量，各自使用独占GPU，共享CPU。每档新建embedding对象与文本缓存；模型服务跨档保留prefix/JIT缓存。每档记录独立warmup，wall_seconds不包含warmup和服务启动，包含CPU检索、排队、JSON处理及模型请求。

## 指标解释与研究限制

- 三阶段为初次省略、明确纠正、再次省略；每阶段最多一个澄清，每episode至多6请求。脚本用户回答和纠正由私有金标准控制，不消耗用户模拟模型API。
- successful_episodes 表示协议执行正常，不等于行动全对；行动正确率须查看各阶段 correct_actions。错误阶段以abstain入分母，其他阶段继续测量。
- 控制器的 unsupported_claim_count 实际测量“相对于当前金标准且引用有效证据的断言是否成立”；不完全等于“仅依据模型可见内容是否合理”。若检索遗漏更新，合理依赖旧证据也可能被此计数判错，不能直接称为幻觉。DeepSeek 补充审核仅看公开 observation/response，专门评可见依据，不读取oracle。
- claims允许为空，因此零无依据断言不代表模型完成偏好推断；正式研究需同时报告行动准确、断言覆盖率、提问数、首次直接行动、有效证据召回，不能单看unsupported数量排名。
- 两模板、单次测量不足以给出模型能力结论；变量重复、prefix缓存、短输出会使全量外推乐观。全量须做更多模板先导、人审措辞、明确指标并报告模板级/配对统计。原生工具执行、AppWorld/浏览器、长轨迹不在本次吞吐范围。
- judge为附加语义审核，不能替换已知目标的确定性评分。8例抽查不构成裁判准确率验证，也不代表长期API吞吐/限流承诺。

## 复现入口（仅小规模调试）

```bash
cd /home/tim/Proj/I3Agent
python3 ours1_runtime/manage_services.py start
# 等待 localhost:8020/v1/models 与 :8021/v1/models 均可访问
python3 ours1_runtime/launch_batch.py parallel4
python3 ours1_runtime/manage_services.py stop
```

launch_batch会同时启动两模型客户端；每模型每项目8例×两基线。全量运行保持关闭，未训练。重新执行judge时应使用新的输出目录，凭据从仓库外 deepseek.env.sh 读取，不能写入代码或日志。

## 实测结果与效率外推（2026-11-02）
设备：双RTX4090，每模型各一张；Qwen3-8B关闭thinking，gpt-oss-20b low reasoning。每个档位每模型32个episode，两个基线各16个。以下时间不含预热；一次测量，非置信区间。

### serial
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-013619-serial`
- Qwen3-8B: 160.89s / 32 episodes，11.93 episodes/min；协议正常 32/32，请求 144，p50/p95 1.239/1.313s；端到端输出 53.6 tokens/s，截断 0。CPU embedding编码累计 10.73s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 60，规则不支持断言 16。
- gpt-oss-20b: 90.84s / 32 episodes，21.14 episodes/min；协议正常 24/32，请求 136，p50/p95 0.443/1.401s；端到端输出 165.5 tokens/s，截断 0。CPU embedding编码累计 10.80s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 9, 16]/16；澄清 32 次，断言 20，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 11, 12]/16；澄清 8 次，断言 21，规则不支持断言 1。

### parallel4
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-013910-parallel4`
- Qwen3-8B: 45.88s / 32 episodes，41.85 episodes/min；协议正常 32/32，请求 144，p50/p95 1.322/1.403s；端到端输出 188.0 tokens/s，截断 0。CPU embedding编码累计 11.52s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 55，规则不支持断言 9。
- gpt-oss-20b: 33.53s / 32 episodes，57.26 episodes/min；协议正常 27/32，请求 136，p50/p95 0.669/1.639s；端到端输出 387.4 tokens/s，截断 0。CPU embedding编码累计 11.21s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 10, 16]/16；澄清 32 次，断言 19，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 13, 12]/16；澄清 8 次，断言 22，规则不支持断言 3。

### parallel8
结果目录：`/home/tim/Proj/I3Agent/ours1_runtime/runs/20261102-014005-parallel8`
- Qwen3-8B: 27.80s / 32 episodes，69.05 episodes/min；协议正常 32/32，请求 144，p50/p95 1.341/1.428s；端到端输出 310.2 tokens/s，截断 0。CPU embedding编码累计 12.02s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 32 次，断言 48，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 16, 16]/16；澄清 16 次，断言 56，规则不支持断言 10。
- gpt-oss-20b: 25.07s / 32 episodes，76.58 episodes/min；协议正常 25/32，请求 136，p50/p95 0.766/2.030s；端到端输出 557.1 tokens/s，截断 0。CPU embedding编码累计 12.43s（含在wall time中，并发时不可直接相加）。
  - current_session: 阶段0/1/2正确动作 [16, 10, 16]/16；澄清 32 次，断言 14，规则不支持断言 0。
  - history_retrieval: 阶段0/1/2正确动作 [16, 13, 12]/16；澄清 8 次，断言 27，规则不支持断言 4。

### DeepSeek Flash补充裁判
8/8 成功，4并发耗时 2.86s，prompt/completion tokens=14974/765。输出 `../ours1_runtime/judge-audit-final/`。抽样按模型×项目×基线覆盖8格，包括协议失败案例，不按成功筛掉困难样本。仅将公开轨迹发送云端。

### 全集耗时估计
全集4608个episode×2基线×2模型=18432次模型episode；每模型9216次。两卡同时运行，以较慢模型结束时间为准。
- 按serial实测吞吐线性外推：两卡约 12.87 小时（仅本地actor阶段）。
- 按parallel4实测吞吐线性外推：两卡约 3.67 小时（仅本地actor阶段）。
- 按parallel8实测吞吐线性外推：两卡约 2.22 小时（仅本地actor阶段）。
考虑64模板的新文本、较少缓存复用、输出长度和CPU检索差异，以8并发估计预留 3.3–6.7 小时；这是预算余量而非统计区间。先导256个episode×两基线×两模型=1024次模型episode，理想用时为全集的1/18，另加启动/预热。
若每个模型episode都做一次同等长度judge审核，按本次4并发样本粗推另需约1.83小时（串行阶段相加；流水线可重叠）。该推算仅8例，不能代表长期速率、费用或限流。确定性行动评分覆盖全部即可，语义审核可先抽5–10%并检查争议例。

### 验收与保留限制
- tim环境323个包版本和conda安装历史哈希均未改变；两个来源项目和快照的15584/64个源码文件均与原manifest一致。
- 未启动全集、训练或原生工具执行；执行开关仍禁止全集。所有初始失败日志与模型非法动作保留。
- 首次服务启动至ready约44s（Qwen）/53s（gpt-oss）；gpt-oss首次请求约41s，后续显著缩短，已计入单独warmup。首次编译缓存与已有缓存有关，不能保证未来冷启动耗时相同。

## 收尾与裁判配置修正

- DeepSeek初轮未显式关闭thinking，1024 token上限造成5/8响应截断，保留于 ours1_runtime/judge-audit/。最终显式设置thinking.type=disabled，仍使用1024上限，8/8成功，4并发2.86s；输出token共765。参考官方参数文档：https://api-docs.deepseek.com/guides/thinking_mode/ 。未安装新SDK。关闭thinking会改变裁判模式，本轮只验证接口和吞吐，正式实验应固定并验证裁判设置。
- 最终judge脚本也保留协议错误的原始模型输出供审核，不能用成功样本筛选掩盖模型错误。
- 三档gpt-oss错误分别8/32、5/32、7/32，均为Invalid commit，未观察到HTTP超时或token截断；Qwen三档均32/32协议正常。并发批处理下即使temperature=0/seed=42也不能据此保证完全一致，正式结论需要重复与模板级统计。
- 结果汇总保存于 ../ours1_runtime/calibration-report.json 与 calibration-results.md；新增 collect_results.py 汇总脚本和 update_docs.py 文档脚本，所有差异仅位于ours1侧与共享runtime。
- 已停止本轮两个vLLM服务，释放GPU；未改变其他用户服务。重启使用上述manage_services.py start。
