# G2 整改自核销 — fig1 二次改版轮（2026-10-09 深夜）

- **审查**：slam-critic G2 判决档，报告 `/tmp/slam_critic_g2_fig1_overview_2026-10-09.md`，
  结论 **Reject（1 致命 + 5 重大 + 4 次要）**；审查对象 commit `3794f4339`。
- **整改 commit**：`a70c87f53`。G4 复核（同 critic）结论见文末。

## 致命（1）销项

| # | 问题 | 整改 | 验证 |
|---|---|---|---|
| C1 | `mask_overlay` 把 0-255 域颜色写进 0-1 float 图 ⇒ 面板 2 背景截成纯黑，实为黑底剪影，与图注"照片叠掩码"相反 | `clip8` 显式按域缩放 + `mask_overlay` 域自适应（0-1 域颜色同步 /255）、输出统一 0-1 float | 重出图目检 = 照片背景 + 橙半透掩码 + 轮廓；**固化门** `test_fig1_mask_panel_is_photo_backed`（面板 2 背景亮度中位数 >0.30）；**阴性对照实测** = 旧缺陷版 0.000 会红 |

## 重大（5）销项

| # | 问题 | 整改 |
|---|---|---|
| M1 | outline 公式恒空：`edge = m & ~dilate(m) = ∅` | 改 `dilate(m) & ~m`（人形轮廓可见） |
| M2 | 图注 "+6.8 dB **median**" 与实算（三序列 median 的 mean）矛盾 | 图注改 "mean over sequences of the per-sequence median dynamic-region PSNR gain" |
| M3 | 图内 6.0× vs 图注 5.96× 同数两精度无绑定 | 图注补 "5.96×, i.e. 6.0× rounded" |
| M4 | 工件只在 /tmp/fig1_assets，可复现链断裂（与上轮 G2-M1 同类两连发） | 导出脚本入库 `scripts/02_analysis/paper2_fig1_export_assets.py`（实测 rc=0，dyn frac 0.150 与原探针一致）+ PROVENANCE 两步命令 + overview docstring 改引 |
| M5 | codec 面板 f00240 与其余面板 f621 异帧未声明 | 图注补 "codec panels use frame 240" |

## 次要（4）销项

S1 PROVENANCE v1 段加退役分隔线 ✅ / S2 守护测试常量加历史锚注（`AI_FIG_ASPECT_V1_RETIRED`）✅ /
S3 `die()` 改 `!= 42` 精确白名单（防口径静默漂移）✅ / S4 "track (pose↔map)" 有效 ~6.2pt 贴 floor：
本轮 width 0.80→0.76 后 ~5.9pt，仍贴线——登记为印刷打样时核查项，不阻塞电子稿。

## 门（整改后自跑）

编译 **14 页（=上限）/ 0 overfull / 0 undefined ref**（图注增高 6.3pt ⇒ width 0.80→0.76 回补）；
守护 **7 测**（新增 C1 固化门）；nature-figure collision audit PASS + text audit PASS（最小内嵌 7.6pt）；
全量 **587 passed**；health 0 FAIL；三方一致 `a70c87f53`。

## G4 复核结论（同 critic，2026-10-09 深夜）

**Accept** — 上轮 1 致命 + 5 重大 + 3 次要全部核销，阴性对照实测真红，无整改引入型缺陷。逐条亲测证据：
- C1 销：新 mask_overlay 输出 corner=(155,155,149)（照片背景在）；固化门旧缺陷 PNG median=0.0000→RED、新 PNG 0.6941→PASS
- M1 outline 销（dilate&~m）；M2 措辞与算法逐字相符；M3 精度绑定在；M4 导出脚本独立重跑 rc=0、6 个 .npy 逐位一致、重渲 PNG 与提交版逐位一致；M5 帧号在
- S1/S2/S3 销；内容语义门在位且阴性对照真红
- 整改引入：无致命/重大。提示级 2 条不阻塞：① 0.76\linewidth 后面板小字有效 ≈5.9pt 贴 5pt floor（终稿打样确认）；② test:85 报错文案仍写"AI 版回退锚点"（实为程序版留档），纯文案
- G4 轮已追加至 /tmp/slam_critic_g2_fig1_overview_2026-10-09.md
