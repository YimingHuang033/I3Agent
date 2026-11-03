# BBQCard2 上的本地适配与试运行记录

记录日期：2026-10-30（Asia/Hong_Kong）。目标目录：`/home/tim/Proj/I3Agent/Pi-Bench`。

> 最新状态：原版 researcher_task_013 单任务已完成真实 agent 交互、COMP/PROC 评分和产物导出，容器退出 0。COMP=0.9354838709677419，PROC=0.6666666666666666。最终复现入口为 scripts/run_minimal_bbqcard2.sh；第 12 节记录结果。前面缺少 Docker/未运行的说明均为排查历史。

## 1. 原版基线与获取方式

- 官方仓库：`https://github.com/Simplified-Reasoning/Pi-Bench.git`。
- 当前基线提交：`4f545be5d289b28ff022d2904d455007358ed3b7`（Update README.md，2026-10-13）。本次没有确认这是远端最新提交。
- BBQCard2 直接 `git clone` 因 `GnuTLS recv error (-110)` 失败。改用本机已有的同一官方仓库，生成 Git bundle 后经 SSH 传输。
- 本机来源是浅克隆，bundle 没有父提交对象，远端直接 clone bundle 因缺少父提交失败。因此在远端初始化仓库，写入相同的 shallow 边界，导入 bundle 的 pack，恢复 main 到上述提交，并设置官方地址为 origin。
- `git fsck --connectivity-only` 已通过。此方法保留该提交的原始 Git 对象与工作树内容；它不是完整历史克隆。没有伪造提交或改写基线代码。

## 2. 与原版代码和配置的差异

本次不修改原版已跟踪的业务代码、数据集、Docker 启动器或默认 `deepseek-v3.2.yaml`。

新增文件：

1. `config/models/deepseek-flash.yaml`：本地试运行模型配置。
   - 被测模型从示例中的 `deepseek-v3.2` 改为凭据文件指定且接口实际可用的 `deepseek-flash`。
   - provider 显式指定为 `custom`，使用项目自带的 OpenAI-compatible provider。
   - 原版 DeepSeek 配置的模拟用户与评审模型均为 `gpt-5.4`；本次两者都替换为 `deepseek-flash`，因为任务指定使用 DeepSeek 凭据。
   - 三种角色分别使用原版已有的 `MODEL_*`、`USER_*`、`JUDGER_*` 环境变量，实际连接同一 DeepSeek endpoint 和同一凭据。
   - 模拟用户、评审的 `max_concurrency` 都设为 1，`max_retries` 都设为 2，用于小规模接通验证。
   - 保留 `BRAVE_SEARCH_API_KEY` 环境变量接口；当前值为空，未配置 Brave Search，因此不能认为网页搜索能力已具备。
   - HTTP/HTTPS/no_proxy 字段显式设为 null，与原版 DeepSeek 配置一致。
2. `env.sh`：仅 source 仓库外的 `/home/tim/Proj/I3Agent/deepseek.env.sh`；不直接保存密钥，权限设为 600。原版 `.gitignore` 已忽略此文件，无需修改 `.gitignore`。
3. `modify.md`：本文档，记录本次所有本地差异、验证范围与限制。

这些模型替换会改变用户模拟和评分行为。本次结果只能用于环境/兼容性验证，不能直接当作论文的 DeepSeek-V3.2 + GPT-5.4 设置或排行榜复现结果。

## 3. 仓库外新增文件与环境

以下路径均位于 `/home/tim/Proj/I3Agent/`，记录在这里以便完整追溯：

- `.venv-pibench311/`：实际使用的独立 Python 3.11.14 venv，创建解释器来自 `/home/tim/miniconda3/envs/tim/bin/python`。不修改原有 conda 环境。
- `.venv-pibench/`：最初使用 base Python 3.13.11 创建的备用 venv；发现已有 Python 3.11 后改用前项。此目录未用来运行评测。
- `pi-bench.bundle`：通过 SSH 传入的原版 Git 数据。
- `deepseek.env.sh`：权限 600；从 `/home/tim/Proj/changyong.txt` 的 DeepSeek 配置段提取凭据，导出三种角色的 API 地址和密钥。该文件包含真实凭据，不应提交或公开。
- `setup_pibench.py`：本次环境准备脚本；安装两个 editable 包、创建本地模型配置和启动脚本，最后尝试启动单任务。由于 Git 传输过程中的修复，目前脚本要求仓库已存在，不是独立通用安装器。
- `run_pibench_smoke.sh`：进入仓库、激活 venv、加载 env.sh，然后运行 `pibench --model-id deepseek-flash --user-id researcher --task-id researcher_task_001`；附加参数透传。
- `smoke_deepseek.py`：通过 Pi-Bench 的 `LLMClient` 和 NanoBot 的 `CustomProvider` 测试真实 DeepSeek 请求；后者验证 echo 工具调用及工具结果返回。该 echo 在测试脚本内处理，不运行 shell，不等同于完整 AgentLoop/评测任务。
- `setup-logs/`：依赖安装、启动尝试以及 API smoke 测试日志/结果。

安装使用阿里云 PyPI 镜像（命令级 `-i https://mirrors.aliyun.com/pypi/simple/`），没有修改用户或系统的全局 pip 配置。安装方式为 `pip install -c constraints.bbqcard2.txt -e . -e third_party/nanobot`，除下述显式版本约束外，其余依赖按原版声明解析。

## 4. 安全与密钥处理

密钥只在远端读取和使用。本文档、模型 YAML、启动命令和聊天中均不写密钥值。原始 `changyong.txt` 未修改。`deepseek.env.sh` 位于仓库外，`env.sh` 已由原版忽略规则排除。不要将运行时生成的含凭据配置公开。

## 5. 验证与当前状态

- SSH 已连通，路径已建立。
- DeepSeek `/models` 请求成功，返回可用的 `deepseek-flash`。
- DeepSeek 原始 `/chat/completions` 请求成功，测试提示返回 `OK`。
- Git 对象连通性检查通过。
- Pi-Bench 和仓库内 NanoBot editable 安装完成；`python -m pip check` 输出 `No broken requirements found.`。
- Pi-Bench `LLMClient` 真实调用成功，返回 `OK`。
- NanoBot `CustomProvider` 真实工具调用成功：请求 echo(text="pi-bench-ok")，脚本提供工具返回值后，模型回复 `pi-bench-ok`。包括 reasoning_content 的后续请求兼容性已在这一轮交互中验证。
- 官方 pibench 启动器已实际执行单任务启动命令，成功读取本地配置并选择 researcher / deepseek-flash / 单次运行，随后退出码为 1，报错 `[pibench] docker command not found or unavailable`。因此 benchmark 主流程没有执行。
- `git diff --exit-code` 通过：原版跟踪文件与基线一致。新增可见文件仅为 `config/models/deepseek-flash.yaml`、`constraints.bbqcard2.txt`、`modify.md`；另外新增被原版忽略的 `env.sh` 和启动器创建的 `outputs/` 空目录。

## 6. 完整评测的前置条件和限制

- 系统 PATH 中无 Docker，未发现 `/var/run/docker.sock` 或 `/run/user/1001/docker.sock`。
- `sudo -n true` 失败，当前任务没有使用 sudo 密码或修改系统服务。
- 虽然 unprivileged user namespace 可用，但 `newuidmap`/`newgidmap` 不可用，尚无可用的 rootless Docker 环境。
- 未执行 `docker pull zzzhr97/pi-bench:latest`；尚未安装和下载 AppWorld 数据。
- 没有把官方 Docker 流程替换成宿主机直接执行 agent 工具的流程。
- 当前只尝试 researcher 的第一个任务，没有发起全量 100 任务或 3 次重复评测，也没有 PROC/COMP 分数。

待 Docker 与 AppWorld 就绪后，单任务启动入口为：

```bash
ssh BBQCard2
cd /home/tim/Proj/I3Agent/Pi-Bench
source ../.venv-pibench311/bin/activate
source env.sh
bash scripts/setup_appworld.sh
docker pull zzzhr97/pi-bench:latest
../run_pibench_smoke.sh
```

这段命令要求 Docker 已安装且 tim 用户有访问权限；它不负责安装 Docker。Brave Search 仍需单独配置。上述前置条件未满足时，不应将 API 接通误认为完整 benchmark 已跑通。

## 7. 安装过程中新增的兼容性约束

新增 `constraints.bbqcard2.txt`，只包含 `lark-oapi==1.5.3`。原版 NanoBot 要求 `websockets>=16.0,<17.0`，而 PyPI 上当前 lark-oapi 1.7.5 要求 `websockets>=11,<16`，1.6.0 要求 `<14`；pip 为此反复回溯并下载多个大包。查询 1.5.3 的发布元数据确认其 websockets 没有冲突的上限，且 1.5.3 位于原版 `lark-oapi>=1.5.0,<2.0.0` 范围内。因此终止第一次依赖解析并增加此约束重试。没有修改第三方 pyproject.toml，也没有放宽原版依赖要求。此约束只用于当前安装，未验证飞书通道功能。`setup_pibench.py` 同步增加 `-c constraints.bbqcard2.txt` 参数。

## 8. 最终验证证据与后续使用

日志和结果位于 `/home/tim/Proj/I3Agent/setup-logs/`：

- `dependencies.log`：基础依赖安装记录。
- `setup.log`：第一次无额外约束的安装记录；由于 lark-oapi 与 websockets 冲突回溯而手动终止，此日志不是最终安装结果。
- `setup-constrained.log`：添加约束后的完整安装，包含 `SETUP_COMPLETE` 与 `LAUNCH_EXIT 1`。
- `launch.log`：官方 pibench 启动器实际报错，缺 Docker。
- `benchmark-client-smoke.json`：单独的 Pi-Bench 客户端测试结果。
- `deepseek-smoke.json`：最终 Pi-Bench 客户端 + NanoBot 工具调用往返测试结果。
- `requirements-installed.txt`：安装完成后的 pip freeze 版本快照，用于追溯当前环境；包含 editable 本地路径，不是跨机器通用锁文件。

关键已安装版本：Python 3.11.14、pibench 0.1.0、nanobot-ai 0.1.4.post3、lark-oapi 1.5.3、websockets 16.1.1、litellm 1.106.6、openai 2.54.0。基础安装时的 openai 3.41.0 与 rich 15.0.0 已由最终依赖解析器自动调整为兼容版本；没有修改这些包的源码。

NanoBot provider 导入时，LiteLLM 从 raw.githubusercontent.com 获取模型成本表失败，自动回退到包内备份。该网络警告未影响本次 custom provider 请求；没有修改 LiteLLM 行为，也没有验证成本统计准确性。

重新执行不依赖 Docker 的 API/工具接通测试：

```bash
cd /home/tim/Proj/I3Agent/Pi-Bench
source env.sh
../.venv-pibench311/bin/python ../smoke_deepseek.py
```

该命令会产生少量真实 API 用量，并覆盖 `deepseek-smoke.json`。完整 benchmark 仍需第 6 节列出的 Docker、镜像、AppWorld 以及按需配置的搜索凭据。当前没有留下正在运行的 benchmark/agent 服务。

## 9. 后续操作：安装 Docker 并拉取官方镜像（2026-10-30）

用户随后要求拉取镜像，并提供 sudo 验证用于执行安装。密码仅经 sudo 交互输入，不保存在配置、脚本或本文中。

系统级新增操作：

- 执行 `apt-get update` 和 `apt-get install -y docker.io`，安装 Ubuntu 源的 Docker 29.1.3 及 containerd、runc、bridge-utils、pigz、ubuntu-fan 依赖。
- apt 尝试配置系统原先已处于未完成状态的 flatpak、postfix 时，因 `useradd: cannot open /etc/passwd` 报错并返回 100。Docker 相关包本身已安装。没有修改这两个无关软件包或其服务配置，也没有修改 passwd 文件。
- 单独执行 `systemctl enable --now docker`，Docker daemon 已启动；服务启用会保留。没有将 tim 加入 docker 组，当前使用 sudo 操作 Docker。
- 直连官方 Docker Hub 超时/失败，保存到 `../setup-logs/docker-pull-direct.log`。
- 为拉取镜像，临时通过 SSH reverse forwarding 将远端 `127.0.0.1:39873` 转到本机 `127.0.0.1:39872` 的 CONNECT 代理。本机临时脚本路径为 `/private/tmp/i3agent-docker-connect-proxy.py`，仅允许官方 registry/auth/CDN 的 443 端口，不解密 TLS；SSH 仅监听远端 loopback。
- 临时创建 `/run/systemd/system/docker.service.d/pibench-pull-proxy.conf`，设置 Docker daemon 的 HTTP_PROXY/HTTPS_PROXY 为上述地址，NO_PROXY 为 localhost、127.0.0.1 和 `.r2.cloudflarestorage.com`。R2 镜像层 CDN 经检查可从服务器直接连接，因此大文件尽可能直接下载。
- 重新加载 systemd 并重启 Docker，执行 `docker pull zzzhr97/pi-bench:latest`；日志为 `../setup-logs/docker-pull.log`。完成后移除临时代理配置和连接，最终结果在下方补充。

镜像 Linux/amd64 manifest 预检摘要为 `sha256:3bdb960745315514150e97e7e867110ed797a51e3ae1abec94634e473ee8e41a`，13 层，压缩大小约 318 MB。最终以服务器 Docker 的 RepoDigests 为准。这一操作不修改 benchmark 的源代码或模型配置。

网络排查补充：本机可访问 Docker Hub，服务器直连 registry/auth/CDN 失败；SSH 连接经 Tailscale DERP(sin) 中继，未建立直连。代理允许列表后来补充实际重定向使用的 `production.cloudfront.docker.com`。为缩短等待，还只读检查了 DaoCloud、dockerproxy.net 和 docker.1ms.run 的公共缓存：前者拒绝/后者连接失败，1ms 的 manifest 与上述官方摘要一致但 blob 请求返回 403。因此未采用这些镜像站的镜像内容，没有配置 registry-mirrors，实际镜像下载仍经临时 SSH 通道访问 Docker Hub 官方 CDN。临时只读探测文件 `/tmp/pibench-mirror-manifest.json` 已删除。

## 10. 镜像拉取最终结果与清理

- `docker pull zzzhr97/pi-bench:latest` 已成功，日志包含 `Status: Downloaded newer image for zzzhr97/pi-bench:latest`。
- RepoDigest：`zzzhr97/pi-bench@sha256:3bdb960745315514150e97e7e867110ed797a51e3ae1abec94634e473ee8e41a`，与本次拉取前直接向官方 registry 查询的 Linux/amd64 manifest 摘要一致。
- 平台 linux/amd64，Docker inspect 报告 Size 为 318332387 bytes。Docker image store 使用 containerd 后端；该 Size 字段不用于估算所有解压后的磁盘占用。
- 镜像保存在系统 Docker/containerd image store，不在 Git 仓库目录内。
- 已删除 `/run/systemd/system/docker.service.d/pibench-pull-proxy.conf`，执行 daemon-reload 并重启 Docker；`systemctl show docker -p Environment` 为 `Environment=`，没有残留代理环境变量。
- 已停止 SSH reverse forwarding 和本机 CONNECT 代理进程，并删除本机临时代理脚本。没有修改 `/etc/hosts`、系统 DNS 或 `/etc/docker/daemon.json`，也没有配置永久镜像加速站。
- Docker 服务保持启用并运行。tim 没有新增 docker 组权限，需用 `sudo docker ...`。原有 `run_pibench_smoke.sh` 没有改为自动 sudo；完整评测尚未重跑。
- 清理代理后执行无网络容器验证：`docker run --rm --network none --entrypoint python zzzhr97/pi-bench:latest ...`，退出码 0，Python 3.11.15，`nanobot`、`appworld` 两个模块均存在。此测试只检查容器和包的可用性，不代表 AppWorld 数据或完整评测已就绪。测试容器已自动删除。
- 证据：`../setup-logs/docker-image-inspect.json`、`../setup-logs/docker-container-smoke.log`、`../setup-logs/docker-pull.log`。这些日志已归属 tim，便于后续查看。

查看已拉取镜像：

```bash
sudo docker image inspect zzzhr97/pi-bench:latest
```

系统已有的 flatpak/postfix 包配置错误仍未处理，不影响本次已经验证成功的 Docker 服务和容器启动。本轮没有修改 benchmark 已跟踪文件、模型参数或密钥。

## 11. 最小端到端运行：选择、修复与复现入口

后续用户要求跑通最小运行单元。本轮采用原版 `researcher_task_010`（LiteAlign 审稿意见分类及 LaTeX 回复提纲），只跑 researcher、deepseek-flash、一个任务、一次重复，保留原版 run + eval 两阶段和 COMP/PROC 两类评分。该任务在原版 episode 中无前置依赖，类型为 short_term_independent，输入文件 `litealign_comment.txt` 随仓库提供。不改任务文本、隐藏意图、评分逻辑或输入素材。

最初按 researcher_task_001 启动做环境排查（日志 `../setup-logs/minimal-run-01.log` 和 `minimal-run-02.log`），依次发现：

1. `tools.brave_search_api_key` 引用空的 `${BRAVE_SEARCH_API_KEY}`，严格环境变量校验报错，容器尚未进入任务。修复：只在新增的 `config/models/deepseek-flash.yaml` 中将该字段改为字面量空字符串 `""`，并同步仓库外 `setup_pibench.py` 的配置模板，避免重新安装后恢复错误。没有提供假 key，也没有修改原版校验代码。Brave web_search 仍不可用。因此最小验证改用不依赖外网搜索的原版独立短任务 010，而不是需要搜索论文的 001。
2. AppWorld API 启动报 `The appworld package is not fully installed`。修复：用官方镜像已有的依赖执行 `python -m appworld.cli install --repo`，将 `third_party/appworld` 挂载至镜像原路径 `/opt/proactive/appworld`；使用宿主机 tim 的 UID/GID 1001:1001，且 `--network none`。这一步成功解包原版 apps、package-tests、task generation、data generation bundles。没有在宿主机额外 pip 安装 AppWorld，也没有下载/替换现有 data 目录。仓库原有 data 约 67 MiB，API/MCP 在此基础上已启动；这不代表完整 AppWorld 数据库操作均已验证。

解包产生的本地文件/目录包括 `third_party/appworld/tests/`、`generate/data/`、`generate/tasks/`，以及各 apps 子目录下的 `README_BEFORE_SHARING.md`；其他文件由上游 bundle 还原或命中原版忽略规则。没有编辑这些文件的内容，也没有修改原版 Git 已跟踪文件。这些属于安装生成物，未提交。

新增本地复现脚本：

- `scripts/setup_appworld_bbqcard2.sh`：以官方镜像离线解包 AppWorld 安装素材；Docker 无访问权限时通过 sudo 重启自身，使用宿主机素材所有者 UID/GID 创建文件。
- `scripts/run_minimal_bbqcard2.sh`：自动处理 Docker sudo 权限、设置 `umask 077`、激活仓库外的 Python 3.11 venv、加载 `env.sh`；若 AppWorld package-tests 未解包则调用上述脚本；运行 `pibench --model-id deepseek-flash --user-id researcher --task-id researcher_task_010 --run 1 --output-dir outputs/minimal-deepseek-flash`。保留 AppWorld 集成，没有使用 `--disable-appworld`。只接受可选的 `--rerun-failed` 参数，避免改变任务/输出目录或提前删除待导出容器。
- `scripts/finalize_minimal_bbqcard2.py`：成功后从对应已停止容器导出 workspace 和 trace_logs 到 runtime 的 `artifacts/`；对原版 launcher 保存的 `inspect.*.log` 中真实 API 密钥做脱敏；把专用输出树归还给 tim/调用 sudo 的用户，顶层权限保持 700。只修改这次运行的诊断文件和权限，不修改模型输入、轨迹或评测结果。

原版 launcher 的 Docker inspect 日志会包含环境变量中的真实密钥。测试启动时已使用 `umask 077` 限制访问，不在聊天中展示原始 inspect 内容；上述导出脚本随后对其脱敏。Docker 内部元数据仍由 Docker 权限控制。本轮未把凭据写入新增脚本或文档。

运行命令：

```bash
ssh BBQCard2
cd /home/tim/Proj/I3Agent/Pi-Bench
bash scripts/run_minimal_bbqcard2.sh
```

脚本可能提示 sudo 密码，不保存密码。第一次完整启动日志位于 `../setup-logs/minimal-run-03.log`。已验证 shell 语法与 Python 脚本编译；最终端到端结果在下一节记录。模型、模拟用户、评审都使用 DeepSeek 的差异继续适用，因此单任务分数不用于论文排行榜对比。

### 11.1 从交互任务 010 转到带完整评分的任务 013

010 已成功完成交互，SUCCESS、4 轮、交互 229167 ms，benchmark 239223 ms。原版 010 没有 objectives.checklist，ChecklistEvaluator 因空 criteria 跳过它；ProactivenessEvaluator 对无 criteria 的任务设置 include_in_overall=false。因此独立 PROC=0.3333333333333333（覆盖 1/3 隐藏意图），但 COMP/overall 为 null。这是原版数据定义，不是运行失败，不通过修改评分代码或编造 checklist 来补分。

为验证有效 COMP/PROC，最终入口改为原版 researcher_task_013：同样无前置依赖，使用仓库本地 reviewer_comment.json，有 6 个隐藏意图和 31 条 checklist，产物为 rebuttal.tex。没有迁移 010 的记忆/产物，使用新容器。最终输出根目录改为 outputs/minimal-researcher-013，日志 ../setup-logs/minimal-run-04.log；010 输出保留在 outputs/minimal-deepseek-flash。上述两个辅助脚本的任务/输出选择同步更新。

第一次 010 运行期间编辑了辅助启动脚本，导致核心容器完成后，宿主机脚本收尾出现 syntax error near unexpected token then（退出 2）；这是辅助脚本编辑时序问题，不是 benchmark 失败。已在进程退出后固定脚本并重新做语法检查，以新进程启动 013。010 产物通过单独调用导出脚本成功保存并脱敏，证据 ../setup-logs/minimal-010-export.log。后续没有在运行中改写启动脚本。

最终可重复入口仍为 bash scripts/run_minimal_bbqcard2.sh，现对应 pibench --model-id deepseek-flash --user-id researcher --task-id researcher_task_013 --run 1 --output-dir outputs/minimal-researcher-013。第 11 节中的 010 参数属于排查历史。

## 12. 最小单任务端到端运行最终结果

最终选择原版 `researcher_task_013`，使用本地 `reviewer_comment.json`，无前置任务依赖；运行保持 AppWorld API/MCP、NanoBot、模拟用户以及两类原版评测。没有修改任务文本、checklist、隐藏意图、评测程序或原版已跟踪源代码。

- 任务结果：`Task finished task_id=researcher_task_013 status=SUCCESS turns=3 elapsed_ms=183949 detail=-`。
- 容器结果：`status=exited exit_code=0 started_at=2026-10-30T07:37:18.019818295Z finished_at=2026-10-30T07:44:00.331784586Z oom_killed=false error=`。
- 有效评分任务数：COMP 1、PROC 1。
- COMP：`0.9354838709677419`；PROC：`0.6666666666666666`，均为原版评分输出的 0–1 数值。
- 这仅是单任务接通验证；三种模型角色均为 DeepSeek，且未配置 Brave Search，不能据此报告全量 benchmark 或与论文排行榜直接比较。
- Agent 生成 `rebuttal.tex`（23593 bytes）；保留源码文件，没有宣称它已成功编译为 PDF。容器没有 LaTeX 编译器，agent 轨迹中只有文本/结构检查。
- AppWorld API/MCP 正常启动，但这项文件处理任务没有覆盖 Gmail 等 AppWorld 数据库操作；不能据此声称全部应用场景已验证。

文件位置（相对 Pi-Bench 根目录）：

- 本次 runtime：`outputs/minimal-researcher-013/deepseek-flash/researcher/run/20261030_153717-runtime`。
- 工作区：`outputs/minimal-researcher-013/deepseek-flash/researcher/run/20261030_153717-runtime/artifacts/workspace/`。
- 核心产物：`outputs/minimal-researcher-013/deepseek-flash/researcher/run/20261030_153717-runtime/artifacts/workspace/rebuttal.tex`。
- 原始交互轨迹：`outputs/minimal-researcher-013/deepseek-flash/researcher/run/20261030_153717-runtime/artifacts/trace_logs/`。
- 评分 JSON：`outputs/minimal-researcher-013/deepseek-flash/researcher/researcher_task_013/eval/results/20261030_074044_result.json`。
- 原版轨迹 HTML：`outputs/minimal-researcher-013/deepseek-flash/researcher/deepseek-flash-researcher.html`。
- 服务日志：runtime 下 `service-logs/bench.log`、`nanobot_gateway.log`、`appworld_apis.log`、`appworld_mcp.log`。
- 宿主机完整启动日志：`../setup-logs/minimal-run-04.log`。
- 收尾核验摘要：`../setup-logs/minimal-final-verification.json`。

已验证最终辅助脚本以新进程成功执行，评分非空、容器退出 0、产物与轨迹已导出，并扫描了 16 个最终 inspect/导出文本文件，未发现本次真实 API 密钥。原版 inspect 日志中的密钥已脱敏，最终输出树已归还 tim，顶层权限为 700。早期失败运行保留用于排查，其输出仍受私有目录权限保护，不应直接公开原始 Docker inspect 日志。评测容器保持停止状态，便于检查；没有为复现脚本授予 tim 永久 Docker 组权限。

### 复现

```bash
ssh BBQCard2
cd /home/tim/Proj/I3Agent/Pi-Bench
bash scripts/run_minimal_bbqcard2.sh
```

该命令会使用真实 DeepSeek API 产生用量并启动一个新 timestamp runtime；不要在它运行期间改写启动脚本。若只需复用已成功结果并执行结果导出/检查，可运行：

```bash
bash scripts/run_minimal_bbqcard2.sh --rerun-failed
```

辅助脚本仍使用官方 pibench CLI 和镜像，没有绕过评分、伪造响应、关闭 AppWorld 或放宽任务判定。本轮必要的适配是：Brave 可选字段使用字面量空值、解包 AppWorld 原始安装 bundle、增加三个环境/启动/导出辅助脚本。010 到 013 的任务选择原因及第一次辅助脚本收尾问题见 11.1 节。
