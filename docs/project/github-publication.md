# GitHub收录范围

仓库保存实验实现、受控任务/私有评分oracle、生成器、设计与结果汇总。数据中的private表示对被测模型隔离，不表示包含API凭据；评测时不得让actor读取oracle。

原始benchmark和MemPA personas以固定Git版本的submodule收录。公开ProAgent事件实体保留在benchmarks/data；未加入截图LFS。完整调用轨迹、模型权重、虚拟环境、凭据、缓存和安装包保留在BBQCard2，不上传。

```bash
git clone https://github.com/YimingHuang033/I3Agent.git
cd I3Agent
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init
```

按需要另外拉取原仓库LFS/嵌套子模块；不默认递归下载全部依赖。上游LICENSE及使用限制由各submodule保留，本仓库不代替上游许可。Ours场景改造与原生benchmark分数不可混同。

代码为当前实验的来源快照，保留BBQCard2部署路径；clone不会自动创建模型服务或安装环境。运行说明见ours/runtimes各README。复现须配置已有模型/embedding/DeepSeek环境，并按记录建立隔离项目与runtime的部署对应；不应直接在未配置机器执行历史prepare/monitor。project.py是BBQCard2状态工具，需要相应SSH配置。

ours/projects包含四个Ours实验的新增层及源码快照清单，原始源码由benchmarks/sources提供，不重复上传。public/episodes与private/oracle都完整收录；现有本地工作区的ours/projects此前只在服务器上，此次随仓库补齐。

历史绝对路径与manifest用于记录原运行，不伪装为在新clone下直接可运行的配置。结果汇总不含原始逐次API调用；完整轨迹留在服务器。publication-manifest.json记录新增项目文件来源与SHA256。
