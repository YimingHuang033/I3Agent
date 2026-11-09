# 实际试跑记录

本文件由 `report_runs.py` 从 BBQCard2 原始运行产物生成。失败尝试一并保留。每行是 smoke，不构成统计比较；不同调试版本与预算不能直接作方法消融。token 是接口返回 usage；请求耗时相加不等于并发墙钟耗时。Pi 早期日志仅完整统计 actor 调用。

| 运行 | 方法 | 状态 | 墙钟秒 | 已记录模型调用 |
|---|---|---|---:|---:|
| `.local/runs/lifesim-deepseek-direct` | direct | complete | 29.91 | 14 |
| `.local/runs/lifesim-direct-smoke` | direct | failed | None | 0 |
| `.local/runs/lifesim-direct-v2` | direct | failed | None | 1 |
| `.local/runs/lifesim-direct-v3` | direct | complete | 34.16 | 14 |
| `.local/runs/lifesim-long-p3` | p3 | failed | None | 34 |
| `.local/runs/lifesim-long-p3-v2` | p3 | failed | None | 55 |
| `.local/runs/lifesim-long-p3-v3` | p3 | complete | 113.48 | 52 |
| `.local/runs/lifesim-native` | native | complete | 44.3 | 16 |
| `.local/runs/lifesim-p3` | p3 | failed | None | 29 |
| `.local/runs/lifesim-p3-final` | p3 | complete | 81.42 | 66 |
| `.local/runs/lifesim-p3-v2` | p3 | complete | 74.61 | 66 |
| `.local/runs/lifesim-process` | process | complete | 35.68 | 12 |
| `.local/runs/lifesim-stitch-official` | stitch_official | failed | None | 1 |
| `.local/runs/lifesim-stitch-official-deepseek` | stitch_official | complete | 86.27 | 27 |
| `.local/runs/lifesim-stitch-official-v2` | stitch_official | failed | None | 4 |
| `.local/runs/lifesim-stitch-official-v3` | stitch_official | failed | None | 6 |
| `.local/runs/lifesim-stitch-official-v4` | stitch_official | failed | None | 3 |
| `.local/runs/lifesim-stitch-official-v5` | stitch_official | failed | None | 17 |
| `.local/runs/lifesim-stitch-official-v6` | stitch_official | failed | None | 14 |
| `.local/runs/lifesim-stitch-official-v7` | stitch_official | complete | 88.95 | 12 |
| `.local/runs/mempa-direct` | direct | complete | 66.76 | 17 |
| `.local/runs/mempa-native` | native | failed | None | 0 |
| `.local/runs/mempa-native-v2` | native | failed | None | 0 |
| `.local/runs/mempa-native-v3` | native | failed | None | 1 |
| `.local/runs/mempa-native-v4` | native | complete | 104.04 | 15 |
| `.local/runs/mempa-native-v5` | native | failed | None | 0 |
| `.local/runs/mempa-native-v6` | native | failed | None | 6 |
| `.local/runs/mempa-native-v7` | native | complete | 67.66 | 17 |
| `.local/runs/pi-native` | native | complete | 54.4 | 7 |
| `.local/runs/pi-tools-direct` | direct | failed | None | 9 |
| `.local/runs/pi-tools-direct-v2` | direct | failed | None | 15 |
| `.local/runs/pi-tools-direct-v3` | direct | complete | 181.61 | 27 |
| `.local/runs/pi-tools-native` | native | failed | None | 32 |
| `.local/runs/pi-tools-native-v2` | native | complete | 223.22 | 36 |
| `.local/runs/proagent-inventory` | native | skipped | 0.63 | 0 |
| `.local/suites/methods-v1/p1` | p1 | failed | None | 48 |
| `.local/suites/methods-v1/p2` | p2 | complete | 57.36 | 60 |
| `.local/suites/methods-v1/revoir` | revoir | complete | 64.67 | 60 |
| `.local/suites/methods-v1/stateforge` | stateforge | complete | 45.79 | 20 |
| `.local/suites/methods-v1/stateforge_revoir` | stateforge_revoir | failed | None | 58 |
| `.local/suites/methods-v1/voi` | voi | complete | 49.36 | 41 |
| `.local/suites/methods-v2/p1` | p1 | complete | 84.79 | 66 |
| `.local/suites/methods-v2/stateforge_revoir` | stateforge_revoir | complete | 116.26 | 62 |
| `.local/suites/methods-v2/stitch` | stitch | complete | 41.77 | 18 |
| `.local/suites/methods-v2/stitch_revoir` | stitch_revoir | complete | 74.36 | 52 |

逐项原指标、后端调用量、token、动作计数、来源提交与配置散列见 `run-records.json`。原始对话与 native artifacts 在对应 `.local` 路径。

## 已完成运行的原指标

- `.local/runs/lifesim-deepseek-direct`: `{"IR_explicit": 100.0, "IR_implicit": 0.0, "IC_explicit": 100.0, "IC_implicit": 0.0, "NAT": 80.0, "COH": 100.0, "PA": 28.6, "EA": 100.0, "RR": 0.0}`
- `.local/runs/lifesim-direct-v3`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 20.0, "PA": 14.3, "EA": 60.0, "RR": 100.0}`
- `.local/runs/lifesim-long-p3-v3`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 32.1, "EA": 60.0, "RR": 100.0}`
- `.local/runs/lifesim-native`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 14.3, "EA": 40.0, "RR": 100.0}`
- `.local/runs/lifesim-p3-final`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 28.6, "EA": 60.0, "RR": 100.0}`
- `.local/runs/lifesim-p3-v2`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 60.0, "PA": 14.3, "EA": 60.0, "RR": 0.0}`
- `.local/runs/lifesim-process`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 60.0, "COH": 60.0, "PA": 28.6, "EA": 100.0, "RR": 0.0}`
- `.local/runs/lifesim-stitch-official-deepseek`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 60.0, "COH": 60.0, "PA": 28.6, "EA": 100.0, "RR": 0.0}`
- `.local/runs/lifesim-stitch-official-v7`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 28.6, "EA": 80.0, "RR": 100.0}`
- `.local/runs/mempa-direct`: `{"status": "native_session_completed", "aggregate_scores": null, "reason": "Full original score requires all probes; score flag disabled for bounded smoke"}`
- `.local/runs/mempa-native-v4`: `{"status": "native_session_completed", "aggregate_scores": null, "reason": "Full original score requires all probes; score flag disabled for bounded smoke"}`
- `.local/runs/mempa-native-v7`: `{"status": "native_session_completed", "aggregate_scores": null, "reason": "Full original score requires all probes; score flag disabled for bounded smoke"}`
- `.local/runs/pi-native`: `{"tasks_built": 1, "checklist_evaluated_tasks": 0, "proactiveness_evaluated_tasks": 1, "overall_average_score": null, "overall_proactiveness_average_score": null}`
- `.local/runs/pi-tools-direct-v3`: `{"tasks_built": 1, "checklist_evaluated_tasks": 1, "proactiveness_evaluated_tasks": 1, "overall_average_score": 0.07142857142857142, "overall_proactiveness_average_score": 0.0}`
- `.local/runs/pi-tools-native-v2`: `{"tasks_built": 1, "checklist_evaluated_tasks": 1, "proactiveness_evaluated_tasks": 1, "overall_average_score": 0.42857142857142855, "overall_proactiveness_average_score": 0.5}`
- `.local/suites/methods-v1/p2`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 60.0, "COH": 80.0, "PA": 14.3, "EA": 80.0, "RR": 0.0}`
- `.local/suites/methods-v1/revoir`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 60.0, "PA": 14.3, "EA": 60.0, "RR": 100.0}`
- `.local/suites/methods-v1/stateforge`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 14.3, "EA": 60.0, "RR": 100.0}`
- `.local/suites/methods-v1/voi`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 60.0, "PA": 14.3, "EA": 60.0, "RR": 0.0}`
- `.local/suites/methods-v2/p1`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 60.0, "PA": 14.3, "EA": 80.0, "RR": 0.0}`
- `.local/suites/methods-v2/stateforge_revoir`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 28.6, "EA": 80.0, "RR": 100.0}`
- `.local/suites/methods-v2/stitch`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 60.0, "COH": 60.0, "PA": 14.3, "EA": 80.0, "RR": 100.0}`
- `.local/suites/methods-v2/stitch_revoir`: `{"IR_explicit": 0.0, "IR_implicit": 0.0, "IC_explicit": 0.0, "IC_implicit": 0.0, "NAT": 40.0, "COH": 40.0, "PA": 28.6, "EA": 60.0, "RR": 100.0}`
