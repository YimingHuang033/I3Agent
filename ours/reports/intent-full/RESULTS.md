# 新增策略全集结果
现有B0/B1仅复用相同任务ID的轨迹；新基线单独运行。受控合成任务探索，无训练，不是原版benchmark分数。
纠正优先为文本规则，其命中受明确措辞影响；full-history上下文更长，属于诊断参照。
规则unsupported不等于完整语义无依据假设；judge仅补充审核。

- gptoss/lifesim_ours1/correction_priority：三阶段最终正确 2200/2304, 1943/2304, 2277/2304；新会话首次直接正确 2132/2304；总问题数 1141；错误episode 304。
- gptoss/lifesim_ours1/current_session：三阶段最终正确 2262/2304, 1889/2304, 2304/2304；新会话首次直接正确 0/2304；总问题数 4516；错误episode 275。
- gptoss/lifesim_ours1/full_history：三阶段最终正确 2092/2304, 2032/2304, 2250/2304；新会话首次直接正确 1954/2304；总问题数 1054；错误episode 216。
- gptoss/lifesim_ours1/history_retrieval：三阶段最终正确 2198/2304, 1964/2304, 1595/2304；新会话首次直接正确 1154/2304；总问题数 1446；错误episode 279。
- gptoss/mempabench_ours1/correction_priority：三阶段最终正确 2673/2688, 2590/2688, 2624/2688；新会话首次直接正确 1982/2688；总问题数 2170；错误episode 55。
- gptoss/mempabench_ours1/current_session：三阶段最终正确 2550/2688, 2365/2688, 2577/2688；新会话首次直接正确 129/2688；总问题数 4878；错误episode 199。
- gptoss/mempabench_ours1/full_history：三阶段最终正确 2681/2688, 2606/2688, 2616/2688；新会话首次直接正确 1441/2688；总问题数 2595；错误episode 68。
- gptoss/mempabench_ours1/history_retrieval：三阶段最终正确 2599/2688, 2577/2688, 2290/2688；新会话首次直接正确 456/2688；总问题数 3396；错误episode 54。
- gptoss/pi_bench_ours1/correction_priority：三阶段最终正确 2164/2304, 2213/2304, 2219/2304；新会话首次直接正确 1972/2304；总问题数 1154；错误episode 78。
- gptoss/pi_bench_ours1/current_session：三阶段最终正确 2301/2304, 2168/2304, 2304/2304；新会话首次直接正确 1/2304；总问题数 4598；错误episode 101。
- gptoss/pi_bench_ours1/full_history：三阶段最终正确 2090/2304, 2175/2304, 2258/2304；新会话首次直接正确 1981/2304；总问题数 1028；错误episode 97。
- gptoss/pi_bench_ours1/history_retrieval：三阶段最终正确 2156/2304, 2219/2304, 1444/2304；新会话首次直接正确 918/2304；总问题数 1426；错误episode 63。
- gptoss/proagentbench_ours1/correction_priority：三阶段最终正确 3261/3264, 2689/3264, 3235/3264；新会话首次直接正确 2889/3264；总问题数 2032；错误episode 439。
- gptoss/proagentbench_ours1/current_session：三阶段最终正确 3262/3264, 2525/3264, 3253/3264；新会话首次直接正确 11/3264；总问题数 6508；错误episode 531。
- gptoss/proagentbench_ours1/full_history：三阶段最终正确 3262/3264, 2700/3264, 3205/3264；新会话首次直接正确 2093/3264；总问题数 2769；错误episode 444。
- gptoss/proagentbench_ours1/history_retrieval：三阶段最终正确 3202/3264, 2679/3264, 2704/3264；新会话首次直接正确 750/3264；总问题数 3635；错误episode 388。
- qwen/lifesim_ours1/correction_priority：三阶段最终正确 2282/2304, 2276/2304, 2262/2304；新会话首次直接正确 1789/2304；总问题数 1827；错误episode 0。
- qwen/lifesim_ours1/current_session：三阶段最终正确 2304/2304, 2256/2304, 2304/2304；新会话首次直接正确 0/2304；总问题数 4608；错误episode 0。
- qwen/lifesim_ours1/full_history：三阶段最终正确 2273/2304, 2252/2304, 2212/2304；新会话首次直接正确 2139/2304；总问题数 1322；错误episode 0。
- qwen/lifesim_ours1/history_retrieval：三阶段最终正确 2280/2304, 2269/2304, 1939/2304；新会话首次直接正确 874/2304；总问题数 2428；错误episode 1。
- qwen/mempabench_ours1/correction_priority：三阶段最终正确 2688/2688, 2685/2688, 2685/2688；新会话首次直接正确 535/2688；总问题数 4177；错误episode 0。
- qwen/mempabench_ours1/current_session：三阶段最终正确 2688/2688, 2570/2688, 2688/2688；新会话首次直接正确 0/2688；总问题数 5376；错误episode 0。
- qwen/mempabench_ours1/full_history：三阶段最终正确 2687/2688, 2687/2688, 2527/2688；新会话首次直接正确 1108/2688；总问题数 3361；错误episode 2。
- qwen/mempabench_ours1/history_retrieval：三阶段最终正确 2686/2688, 2681/2688, 2616/2688；新会话首次直接正确 110/2688；总问题数 4674；错误episode 0。
- qwen/pi_bench_ours1/correction_priority：三阶段最终正确 2284/2304, 2292/2304, 2235/2304；新会话首次直接正确 1412/2304；总问题数 2158；错误episode 0。
- qwen/pi_bench_ours1/current_session：三阶段最终正确 2304/2304, 2304/2304, 2304/2304；新会话首次直接正确 0/2304；总问题数 4608；错误episode 0。
- qwen/pi_bench_ours1/full_history：三阶段最终正确 2271/2304, 2276/2304, 2117/2304；新会话首次直接正确 1951/2304；总问题数 1414；错误episode 3。
- qwen/pi_bench_ours1/history_retrieval：三阶段最终正确 2286/2304, 2291/2304, 1889/2304；新会话首次直接正确 574/2304；总问题数 2654；错误episode 0。
- qwen/proagentbench_ours1/correction_priority：三阶段最终正确 3261/3264, 3199/3264, 3258/3264；新会话首次直接正确 2186/3264；总问题数 3398；错误episode 0。
- qwen/proagentbench_ours1/current_session：三阶段最终正确 3240/3264, 3264/3264, 3240/3264；新会话首次直接正确 0/3264；总问题数 6528；错误episode 0。
- qwen/proagentbench_ours1/full_history：三阶段最终正确 3263/3264, 3263/3264, 2646/3264；新会话首次直接正确 2187/3264；总问题数 2690；错误episode 0。
- qwen/proagentbench_ours1/history_retrieval：三阶段最终正确 3259/3264, 3206/3264, 3258/3264；新会话首次直接正确 162/3264；总问题数 5480；错误episode 0。

缺少轨迹：0；必须结合status.json判断是否运行完成。
详细分阶段指标及缺失清单见analysis.json，来源轨迹哈希见analysis-sources.json。
