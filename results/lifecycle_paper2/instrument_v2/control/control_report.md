# 守卫路径阳性对照 — render_L3_crowd_off_s0_canon（旧码 2864c997 vs 现行码）

> **复跑前提**：需在数据侧机器（远程 3090）执行（run_dir 为仓库相对路径 + 需 GPU 渲染）；
> 本地无该 run 的 PLY ⇒ 本地不可复跑。生成脚本：`scripts/02_analysis/instrument_v2_guard_control.sh`。
- 运行件：`old_render_L3_crowd_off_s0_canon_2864c997.json`（旧码输出）、`../rescore/rescore_L3_crowd_off_s0_canon.json`（现行码输出）
- 逐帧逐参照比对（3 参照 × 17 帧）：
  - 两臂皆有效且**逐位一致**：**6**
  - 新码 `None` 而旧码 `NaN`：**11**（守卫把不可判帧从 NaN 转为 None）
  - 两侧皆缺：34
  - **真不一致：0**

**结论**：✅ 守卫只改可判性、不改数值（真不一致 = 0）
