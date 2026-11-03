# Ours1：运行、监控与结果

BBQCard2 主目录：`/home/tim/Proj/I3Agent`。本地 `ours/runtimes/pi_lifesim/` 是共享运行代码的工作副本，部署到远端 `ours1_runtime/`。

原始 `Pi-Bench/`、`lifesim/` 和各自隔离副本中的上游源码保持不变；仅修改两项目新增的 `ours1/` 与共享运行目录。`tim` 环境不安装、升级或删除包。

## 只需要看这些

- [实验设计](../../docs/experiment-design.md)：研究问题、配对任务和基线。
- 两项目根目录 `modify.md`：与原版的差异、当前授权；完整历史已归档。
- `campaigns/full-20261102-v1/status.json`：运行状态；`monitor.jsonl`：20分钟快照。
- `campaigns/full-20261102-v1/{qwen,gptoss}/episodes/`：逐episode公开输入、输出及私有评估记录。
- 每模型 `summary.json`：完成后汇总；`manifest.json`：冻结代码/数据/配置的SHA256；campaign中的`reproducibility.tar.gz`保存本轮代码/配置/任务材料（不含凭据）。

## 当前队列

两项目各2304条合成任务 × 两基线 × 两模型 = 18432模型episode；每模型9216。优先运行先导子集（每项目128条），随后处理全集剩余任务，不重复跑先导。含development与heldout，不训练、不依据当前结果改提示词；任何设计变更必须使用新campaign。

Qwen3-8B使用GPU0/localhost8020，关闭thinking；gpt-oss-20b使用GPU1/localhost8021，low reasoning。每模型8并发、temperature=0、seed=42、max_tokens=768。CPU运行既有Qwen3-Embedding-0.6B，缓存文本向量；B1取top2历史。服务max_model_len=8192，GPU预留比例0.88。`VLLM_USE_FLASHINFER_SAMPLER=0`绕过本机缺nvcc的sampler路径，未改tim包。

actor完成后对稳定哈希抽取的约5%轨迹做DeepSeek Flash裁判审核，4并发、thinking disabled、max_tokens=1024；凭据仅从外部deepseek.env.sh读取。API开销止于这一轮抽样，不无限重复或自动重试失败。主评分不依赖裁判。

## 操作（BBQCard2）

```bash
cd /home/tim/Proj/I3Agent
# 只读状态
python3 ours1_runtime/monitor.py status
# 首次启动/恢复：独占进程锁防止重复监控
nohup python3 -u ours1_runtime/monitor.py run --interval 1200 > ours1_runtime/logs/monitor.log 2>&1 < /dev/null &
# 停止队列和本轮GPU服务
python3 ours1_runtime/monitor.py stop
```

停止写入campaign的STOP文件，监控最多10秒发现，终止自己创建的客户端与服务。恢复前检查日志、确认旧monitor退出，移除该campaign的STOP文件，再执行启动命令。已有完整checkpoint（包括模型错误）跳过；中断的在途episode可能重做。代码/配置/数据哈希变化会拒绝向旧campaign追加。新实验用`--campaign 新名称`，不会覆盖旧结果。

如果monitor异常退出而服务仍存活，先检查`monitor.pid.json`与两个service.json；不要重复启动。`manage_services.py stop`只停止记录PID和模型路径均匹配的本轮服务，再恢复monitor。端口被其他服务占用时不会接管。

## 监控行为

首次立即执行，之后每1200秒写入一次快照，10秒更新状态；运行完成后释放本轮GPU服务、保持定时监控，直到用户停止。PID在`monitor.pid.json`。无进展15分钟或未知子进程退出会熔断并记录blocked。2026-11-02恢复修正：明确的基础设施错误退出码2会先保存当前批，再等待30秒、重启服务并从checkpoint续跑；连续不足128条进展的恢复最多3次，整个campaign最多24次，超过上限保持blocked。恢复记录在recovery.json，不修改actor或重跑已有结果。模型无效输出单独记失败，保留在分母中继续运行。

当前工具无`notify_on_output`，因此**远端定时监控不会自动唤醒聊天agent或主动发聊天消息**。可直接读status.json，或在聊天中要求查看进度。没有注册cron或第三方通知。

## 文件职责与验收

共享源码共七个：`run_local.py`（执行/续跑）、`protocol.py`（交互/评分）、`manage_services.py`（服务）、`monitor.py`（队列/监控）、`judge_audit.py`（语义抽查）、`check.py`（离线验收）、`analyze.py`（离线汇总）。两个项目的旧脚本入口转发到共享实现。一次性校准脚本/报告在archive，历史runs/logs保持原路径。

离线验收：`lifesim-venv/bin/python ours1_runtime/check.py`；覆盖全部4608个三阶段协议、B0历史隔离、无效动作拒绝、时间顺序、checkpoint身份与原子保存、原始源码哈希，结果在check-report.json。

本轮测量的是合成候选选择，不是AppWorld、网页或原版长工具链。协议成功不等于动作正确。规则unsupported计数依赖当前金标准，须与可见证据语义审核分开；空claims不能证明偏好推断正确。查看逐阶段准确、首次动作、提问、断言覆盖率与模板级/配对结果，不能仅凭吞吐或单一计数排名。

最新完整结果：[全集汇总](../../reports/ours1-full/RESULTS.md)，包含分项目设计与结果。离线汇总命令：`python3 ours1_runtime/analyze.py --campaign full-20261102-v1`（远端）。
