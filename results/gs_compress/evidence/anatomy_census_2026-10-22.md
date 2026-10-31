# §4 解剖统计普查（2026-10-22）

> **用途**：补齐 §4 中此前无生成脚本的两项（各向同性占比、四元数偏离单位模），
> 并提供跨系统与静态场景对照。零 GPU，只读 PLY。
> **工件**：`anatomy_census.json`；生成器：`scripts/gs_compress/anatomy_census.py`。

口径：scale 为 log 域（PLY 直存 log-scale）；`iso_frac` = aniso<0.1 的基元占比，
aniso = log s_max − log s_min；`rot_dev` = |‖q‖−1|>1% 的基元占比；
`infl_*` = span_full / span_p0.1（与 `tail_census.py` 同定义）。
DynaGSLAM 取第 0 时刻位置 `x000..` 与 `rot_000_*`（其 79 字段 schema 无簿记字段）。

| panel | seq | n | infl_scale | infl_xyz | iso_frac | aniso_med | rot_dev |
|---|---|---:|---:|---:|---:|---:|---:|
| ours_dynamic | balloon | 43058 | 1.901 | 1.318 | 0.887 | 0.005 | 0.913 |
| ours_dynamic | balloon2 | 31260 | 1.706 | 1.305 | 0.806 | 0.007 | 0.919 |
| ours_dynamic | crowd | 38599 | 1.488 | 1.392 | 0.866 | 0.004 | 0.940 |
| ours_dynamic | crowd2 | 44257 | 2.117 | 1.313 | 0.877 | 0.006 | 0.903 |
| ours_dynamic | crowd3 | 44469 | 1.853 | 1.339 | 0.907 | 0.004 | 0.909 |
| ours_dynamic | person_tracking | 66078 | 1.779 | 1.396 | 0.831 | 0.005 | 0.922 |
| ours_dynamic | person_tracking2 | 75743 | 1.737 | 1.361 | 0.852 | 0.004 | 0.936 |
| ours_heldout | f1_desk2 | 48757 | 1.623 | 1.309 | 0.705 | 0.006 | 0.945 |
| ours_heldout | f1_room | 145417 | 1.611 | 1.537 | 0.792 | 0.004 | 0.941 |
| ours_heldout | f3_office | 65841 | 1.534 | 1.329 | 0.612 | 0.025 | 0.934 |
| ours_heldout | f3_st_rpy | 108352 | 1.965 | 1.316 | 0.900 | 0.003 | 0.940 |
| ours_heldout | f3_wk_rpy | 93639 | 1.982 | 1.269 | 0.832 | 0.005 | 0.948 |
| ours_heldout | moving_obstructing_box | 63954 | 1.794 | 1.256 | 0.829 | 0.004 | 0.923 |
| dynagslam | balloon | 271365 | 1.280 | 1.470 | 0.000 | 2.320 | 0.985 |
| dynagslam | balloon2 | 264197 | 1.174 | 1.309 | 0.000 | 2.303 | 0.986 |
| dynagslam | crowd | 24152 | 1.244 | 1.223 | 0.000 | 2.552 | 0.968 |
| dynagslam | crowd2 | 37281 | 1.214 | 1.216 | 0.000 | 2.479 | 0.970 |
| dynagslam | mv_no_box | 7292 | 1.348 | 1.411 | 0.000 | 2.438 | 0.972 |
| dynagslam | mv_no_box2 | 4949 | 1.282 | 1.173 | 0.001 | 2.422 | 0.970 |
| dynagslam | person_t | 294977 | 1.287 | 1.412 | 0.000 | 2.344 | 0.972 |
| dynagslam | person_t2 | 297349 | 1.394 | 1.591 | 0.000 | 2.341 | 0.966 |

**读法边界**：本栈与 DynaGSLAM 是两个不同实现，差别不止一处（loss、densify 策略、
时间参数化）；表内差异是描述性的，不作单变量因果归因。
