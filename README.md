# I3Agent

研究多轮交互中的历史偏好保留、纠正更新与必要澄清。模型实验运行在BBQCard2：`/home/tim/Proj/I3Agent`。

- [Ours实验总入口](ours/README.md)：研究设计、四组运行代码、实验结果与改动记录。
- [原始benchmark目录](benchmarks/README.md)：原仓库、配套数据、来源与可用范围。
- [研究草案](docs/research/sketch.md)：概念说明、配图及导出文档。
- [目录维护说明](docs/project/directory-layout.md)：本地/远端对应关系、旧路径兼容与迁移校验。

```text
I3Agent/
├── README.md
├── project.py       # 只读实验状态入口
├── ours/            # 全部自定义实验、结果、设计和历史Ours材料
├── benchmarks/      # 原始benchmark与配套数据
├── docs/            # 研究草案、导出件及项目维护说明
└── archive/         # 通用历史材料和目录迁移清单
```

```bash
python3 project.py status
python3 project.py status intent-full
```

Ours结果是受控偏好选择实验，不等于原版benchmark成绩。原始源码和已冻结实验代码保持独立；本地报告为同步副本。远端根目录旧名称是兼容链接，实际目录已归入`ours/`和`benchmarks/`。

GitHub收录范围、submodule下载与复现边界见[发布说明](docs/project/github-publication.md)。
