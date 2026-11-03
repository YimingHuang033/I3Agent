# 新增策略全集（2026-11-03）

用户授权新增的full-history、correction-priority一并跑完全集。总范围：Pi/Life 4608条 + MemPA/ProAgent 5952条 = 10560条任务；2策略×2模型=42240次episode。校验复用讨论子集192条（包括5条错误记录），实际剩余42048条，不重跑旧B0/B1。

部署目录`/home/tim/Proj/I3Agent/intent_full_runtime`；campaign为`campaigns/full-20261103-v1`。由`i3agent-intent-full-20261103.service`立即后台启动；断开SSH不影响。每10秒状态检查、每20分钟监控快照；模型输出错误保留，连接SDK最多重试2次，服务失败最多3次额外重启（48小时窗口）。没有进度15分钟停止，模型阶段每次进程24小时上限，裁判4小时上限。异常保留日志与checkpoint，不承诺模型全部答对。

```bash
python3 project.py status intent-full
ssh BBQCard2 'systemctl --user status i3agent-intent-full-20261103.service'
# 停止当前全集：
ssh BBQCard2 'systemctl --user stop i3agent-intent-full-20261103.service'
```

完成后生成`RESULTS.md`、`analysis.json`、`analysis-sources.json`及约5%单检查点DeepSeek Flash审核。全部样本复用/配置证据在`reuse-manifest.json`、每模型`manifest.json`、`scheduled-inputs.json`。如仍缺轨迹不可称为全集完成。

不训练，不修改原版benchmark、旧结果、tim环境。full-history是更多上下文的诊断参照；纠正优先是显式中文文本启发式。原B0/B1结果只按相同任务读取用于对照。模型协议错误保留在分母，规则无依据断言仍仅为代理指标，judge未人工校准。详见[修改记录](modify.md)。
