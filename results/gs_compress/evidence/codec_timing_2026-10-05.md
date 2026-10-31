# codec 编解码耗时（2026-10-05）

> **用途**：独立审稿 P1-8。codec 是**离线**后处理，工程论文须报其代价。
> **口径**：CPU 单线程，重复 3 次取均值（含 warm-up）；工件 `rd/codec_timing.json`。

| map | n | encode near/mid/agg (ms) | decode near/mid/agg (ms) |
|---|---|---|---|
| L2_balloon2_baseline_s0 | 26997 | 19 / 32 / 140 | 3 / 4 / 4 |
| L2_balloon_baseline_s0 | 36721 | 27 / 61 / 279 | 5 / 5 / 6 |
| L2_crowd2_baseline_s1 | 41452 | 33 / 85 / 394 | 5 / 6 / 7 |
| L2_crowd3_baseline_s2 | 48378 | 36 / 105 / 406 | 6 / 6 / 8 |
| L2_crowd_final_s0 | 43247 | 31 / 66 / 344 | 5 / 5 / 7 |
| L2_person_tracking_final_s2 | 59346 | 40 / 73 / 334 | 8 / 10 / 8 |

- **near-lossless**：encode 0.724 µs/prim，decode 0.125 µs/prim
- **mid**：encode 1.640 µs/prim，decode 0.144 µs/prim
- **aggressive**：encode 7.377 µs/prim，decode 0.152 µs/prim

> 解读：编解码均为**离线 CPU** 操作，单张地图（数万基元）在 tens–hundreds of ms 量级；扩到十万级基元的量产地图仍在亚秒–秒级。不是在线瓶颈，但也不是零成本。