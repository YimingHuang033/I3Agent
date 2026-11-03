# 原始benchmark与来源数据

本目录收纳现有原始仓库和公开数据；保留其Git元数据、代码和内部布局，不与Ours实现混合。

## 原始仓库

- [Pi-Bench](sources/Pi-Bench/)：主动智能体场景；[代码运行介绍](docs/pi-bench-intro.md)。本地与BBQCard2均已收录。
- [LifeSim](sources/lifesim/)：日常/长程模拟场景；本地与BBQCard2均已收录。
- [MemPABench](sources/MemPABench/)：个性化主动行为来源；本地与BBQCard2均已收录。子模块可用性依原有检出状态，本轮不下载、不补齐。
- [ProAgentBench](sources/ProAgentBench/)：公开数据仓库的既有稀疏检出；本地与BBQCard2均已收录。不是完整原生评测代码，截图LFS未在本轮补齐。
- [PAST-Bench](sources/PAST-Bench/)：已有本地参考仓库，统一纳入索引；未参与当前四来源Ours实验，未额外部署到BBQCard2。

各仓库当前revision及远端地址见[仓库清单](inventory.json)。这是工作区实际状态记录，不是上游最新版声明。

## 配套数据

- [MemPABench-personas](data/MemPABench-personas/)：既有personas数据仓库，保留Git信息。
- [ProAgentBench-events](data/ProAgentBench-events/)：已下载并校验的事件文本实体。

原始benchmark自身的README、许可证和说明保留在源码内部。新增实验和结果统一见[Ours入口](../ours/README.md)，不能将Ours得分当作原版榜单结果。
