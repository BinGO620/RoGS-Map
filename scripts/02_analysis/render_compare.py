#!/usr/bin/env python
"""render_compare.py — 离线渲染对比图与渲染指标（GT | render | depth）。

用途：为已有 run（PLY + trj_full_final.json + config.yml）生成论文用渲染对比图，
并计算与 run 内 eval_rendering 同口径的 PSNR/SSIM/LPIPS/depth-L1。

背景（为什么需要本脚本）：
  1. 仓库原有 run 只落盘 psnr/*/final_result.json 的**数字**，从不保存渲染图像
     （全仓无一张非 evo 的渲染对比 PNG）——WildGS/MonoGS/SplaTAM 论文的
     "GT | rendered | metrics" 图我们一直缺。
  2. Bonn 批次（r33 等）的 psnr json 全部 NaN：根因 = eval_rendering 的
     采样网格 interval=5 与关键帧网格重合（KF 恰好都在 5 的倍数上），
     循环体全程 `continue` → 聚合为空 → NaN。本脚本离线渲染，
     自带采样（--interval 可调），不依赖 run 时 eval，不受该 bug 影响。
  3. 离线重渲染只读 run 产物（PLY/轨迹/config），输出写到独立目录，
     不触碰 run 目录原始输出（D3）。

用法：
  PY=/data/conda_envs/monogs-ours/bin/python
  $PY scripts/02_analysis/render_compare.py \
      --run-dir archive/closed_families/mask_fix_iter/results/local2060_bonn7_balloon_seed0/datasets_bonn/diag_mskfix_bonn_balloon/seed_0/2026-09-12-12-55-55 \
      [--frames 0,100,300,500,800,1100] [--interval 5] [--max-frames 8] \
      [--out-dir /tmp/render_compare/<tag>] [--device cuda:0]

  注：mask_fix_iter 族已于 2026-10-10 归档（Step3c），上例 run 路径随之移到
  `archive/closed_families/`；输出仍应写独立目录（勿写回归档树）。

输出（默认 <out-dir> = results/{exp_id}/render_compare/{run_tag}/）：
  cmp_f{idx:05d}.png      横向拼图 [GT | render]，带 PSNR 文字
  depth_f{idx:05d}.png    对应帧渲染深度（同帧）
  render_metrics.json     同口径 PSNR/SSIM/LPIPS/depth_l1 + 逐帧值
                         + （可用掩码时）静态区/残影指标——见 --mask-subdir
"""

"""静态区/残影指标（2026-09-18 增补，P0）：
  当数据集带冻结动态掩码（Bonn `dynamic_mask_gtmc` 优先；否则 `seg_mask`
  语义类 == --mask-class；**类号由 utils/dynamic_mask_spec 按序列解析**——Bonn 自带
  seg_mask 是 ADE20K 0 起（person=12），本仓 MaskRCNN 生成的是 VOC（15））时，对每帧额外计算
  （函数与运行期 P-A 评估 `utils/static_eval.py` 完全同源）：
    static_psnr / static_ssim / static_lpips / static_coverage /
    static_depth_l1_pen_cm       —— M_static = valid-gt-depth ∧ ¬dynamic
    ghost_excess_depth_l1_cm / ghost_excess_psnr_db / vacated_support_px
                                 —— vacated-vs-background 配对残影对比
  掩码按 **depth 文件名的 timestamp stem** 关联（与运行期协议一致）。
  --no-static 关闭；--no-vacated 关闭残影部分（全序列掩码并集扫描）。
"""
import argparse
import collections
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
os.chdir(REPO)  # dataset_path 是相对路径（datasets/...），与 run 时一致

import cv2  # noqa: E402
import yaml  # noqa: E402
from munch import munchify  # noqa: E402
from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity  # noqa: E402

from gaussian_splatting.gaussian_renderer import render  # noqa: E402
from gaussian_splatting.scene.gaussian_model import GaussianModel  # noqa: E402
from gaussian_splatting.utils.graphics_utils import getProjectionMatrix2  # noqa: E402
from gaussian_splatting.utils.image_utils import psnr  # noqa: E402
from gaussian_splatting.utils.loss_utils import ssim  # noqa: E402
from utils.camera_utils import Camera  # noqa: E402
from utils.dataset import load_dataset  # noqa: E402
from utils.eval_utils import _compute_depth_l1_cm  # noqa: E402


def find_in_run(run_dir, *cands):
    for pat in cands:
        hits = sorted(Path(run_dir).glob(pat))
        if hits:
            return str(hits[-1])
    return None


def sh_degree_from_ply(ply_path):
    """从 PLY header 反推 max_sh_degree（f_rest 数 = 3*((d+1)^2-1)）。"""
    n_rest = 0
    with open(ply_path, "rb") as fh:
        while True:
            line = fh.readline()
            if not line:
                break
            s = line.decode("ascii", errors="strict").strip()
            if s.startswith("property float f_rest_"):
                n_rest += 1
            if s == "end_header":
                break
    if n_rest == 0:
        return 0
    # n_rest = 3*((d+1)^2 - 1) => d = sqrt(n_rest/3 + 1) - 1
    d = int(round((n_rest / 3 + 1) ** 0.5 - 1))
    assert 3 * ((d + 1) ** 2 - 1) == n_rest, f"f_rest 数 {n_rest} 与整 degree 不符"
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="run 的时间戳目录（含 config.yml/point_cloud/plot）")
    ap.add_argument("--frames", default=None, help="逗号分隔的帧列表；缺省按 --interval 均匀采样 --max-frames 帧")
    ap.add_argument("--interval", type=int, default=5, help="缺省采样步长（仅取非关键帧候选）")
    ap.add_argument("--max-frames", type=int, default=8)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--ply", default="final_after_opt", help="final_after_opt | final")
    ap.add_argument("--jpg", action="store_true", help="同时输出 JPEG（q88，便于低带宽回传预览）")
    ap.add_argument("--mask-subdir", default="auto",
                    help="auto | dynamic_mask_gtmc | seg_mask | none（默认 auto：canonical dynamic_mask/，"
                         "缺失即拒——v2 体系不回落 gtmc/seg_mask；legacy 来源需 --allow-legacy-mask）")
    ap.add_argument("--mask-class", type=int, default=None,
                    help="**仅 legacy seg_mask 用**：该 class 像素视为动态（必须显式给）。"
                         "canonical 的 dynamic_mask/ 是 0/255 布尔，不需要类号")
    ap.add_argument("--allow-legacy-mask", action="store_true",
                    help="显式允许历史掩码源（seg_mask/dynamic_mask_gtmc），仅用于复刻历史渲染；"
                         "产物记 mask_validity=legacy。canonical 路径不需要它")
    ap.add_argument("--no-static", action="store_true", help="关闭静态区指标（默认开启，掩码缺失时自动跳过）")
    ap.add_argument("--no-vacated", action="store_true", help="关闭残影（vacated）指标（默认开启）")
    ap.add_argument("--skip-unrenderable", action="store_true",
                    help="渲染失败（如 rasterizer numel 溢出）的帧跳过并计数（协议工具鲁棒性）："
                         "跨臂比较时用 per_frame 记录做帧集交集，勿直接比均值。")
    ap.add_argument("--max-scale-m", type=float, default=0.0,
                    help="仪器护栏：剔除任一轴尺度 > 该值（米）的退化巨基元（不透明度置 −20 使其在栅格化前被剔除）。"
                         "0=关。防 rasterizer numel 溢出；两臂必须同规则使用，剔除计数须入报告。")
    ap.add_argument("--vacated-window-frames", type=int, default=30,
                    help="freshvac 窗口（帧）：只取最近 N 帧新形成的腾空区——跨批稳定口径，"
                         "默认 30 与运行期 Results.static_bg_vacated_window_frames 一致")
    ap.add_argument("--dmax-cm", type=float, default=50.0, help="penalized depth L1 的缺口罚值（cm）")
    ap.add_argument("--a-eval", type=float, default=0.5, help="静态覆盖率判定的渲染不透明度阈值")
    args = ap.parse_args()

    run_dir = str(Path(args.run_dir).resolve())
    cfg_path = os.path.join(run_dir, "config.yml")
    assert os.path.exists(cfg_path), f"no config.yml in {run_dir}"
    config = yaml.safe_load(open(cfg_path))

    ply_path = find_in_run(run_dir, f"point_cloud/{args.ply}/point_cloud.ply", "point_cloud/final/point_cloud.ply")
    trj_path = find_in_run(run_dir, "plot/trj_full_final.json")
    assert ply_path, "no point_cloud PLY"
    assert trj_path, "no trj_full_final.json"

    parts = Path(run_dir).parts
    if "results" in parts:
        ri = parts.index("results")
        exp_id = parts[ri + 1]
        run_name = parts[ri + 2] if len(parts) > ri + 2 else Path(run_dir).name
    else:
        exp_id, run_name = "misc", Path(run_dir).name
    out_dir = args.out_dir or str(REPO / "results" / exp_id / "render_compare" / f"{run_name}_{Path(run_dir).name}")
    os.makedirs(out_dir, exist_ok=True)

    device = torch.device(args.device)
    model_params = munchify(config["model_params"])
    pipeline_params = munchify(config["pipeline_params"])
    background = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32, device=device)

    # ── dataset（读取 GT 图像/深度 + 内参）──
    dataset = load_dataset(model_params, model_params.source_path, config=config)
    dataset.device = args.device
    W, H = dataset.width, dataset.height
    proj = getProjectionMatrix2(
        znear=0.01, zfar=100.0, fx=dataset.fx, fy=dataset.fy,
        cx=dataset.cx, cy=dataset.cy, W=W, H=H,
    ).transpose(0, 1).to(device=device)

    # ── 高斯模型（离线加载 PLY）──
    sh_deg = sh_degree_from_ply(ply_path)
    gaussians = GaussianModel(sh_deg, config=config)
    # 2026-09-22 根因修复（卡 1 栅格化器"故障"）：load_ply 与 render() 内部硬编码
    # device="cuda"（= 当前设备）。--device cuda:1 而当前设备仍为 cuda:0 时，模型张量
    # 与 C++ 内部 workspace 全落卡 0、相机/设置张量落卡 1，栅格化器不做设备检查 ⇒
    # 跨设备裸指针 ⇒ 卡 1 确定性 illegal memory access（sanitize 定位 preprocessCUDA
    # 越界读 4.2MB；物理卡 1 健康：set_device 后同 PLY 成功且输出与卡 0 逐位一致）。
    # 修复 = 把当前设备设为 --device（比逐个搬张量更完整：覆盖未来新增的 "cuda" 硬编码）。
    if str(device) != f"cuda:{torch.cuda.current_device()}":
        torch.cuda.set_device(device)
    gaussians.load_ply(ply_path)
    print(f"[render_compare] PLY={ply_path} n={gaussians.get_xyz.shape[0]} sh={sh_deg} "
          f"model_dev={gaussians.get_xyz.device}", flush=True)

    # ── 轨迹（trj_est = C2W；渲染须 W2C = inv(C2W)）──
    trj = json.load(open(trj_path))
    ids = [int(v) for v in trj["trj_id"]]
    est = [np.asarray(v, dtype=np.float64) for v in trj["trj_est"]]
    pose_by_id = {i: p for i, p in zip(ids, est)}
    N = dataset.num_imgs

    # ── 帧选择：优先非关键帧网格（避免与 KF 网格重合时退化）──
    if args.frames:
        frame_ids = [int(x) for x in args.frames.split(",")]
    else:
        cand = [i for i in range(0, N - 1, max(1, args.interval)) if i in pose_by_id]
        if len(cand) > args.max_frames:
            sel = np.linspace(0, len(cand) - 1, args.max_frames).round().astype(int)
            frame_ids = [cand[i] for i in sorted(set(sel.tolist()))]
        else:
            frame_ids = cand[: args.max_frames]
    print(f"[render_compare] N={N} render frames={frame_ids}", flush=True)

    # ── 评估掩码（掩码体系重构 v2）：唯一来源 <seq>/dynamic_mask/（0/255 布尔，无类号）──
    # 解析入口 utils/dynamic_mask_spec.resolve_eval_mask_dir（**默认拒**，不回落到
    # seg_mask/gtmc——那两套口径已被证伪/废弃，见 evidence/l3_instrument_rescore_2026-09-21.md）。
    # legacy（seg_mask 类号口径）仅作显式逃生门，且必须显式给 --mask-class。
    mask_index, mask_source = {}, None
    mask_class, mask_kind, mask_validity = None, None, None
    if not args.no_static:
        ds_path = config["Dataset"].get("dataset_path", "")
        from utils.dynamic_mask_spec import EVAL_MASK_SUBDIR, resolve_eval_mask_dir  # noqa: E402
        from utils.gtmc_mask import frozen_mask_index  # noqa: E402
        mdir = None
        if args.mask_subdir == "auto":
            mdir, src, legacy = resolve_eval_mask_dir(ds_path)
        elif args.mask_subdir != "none":
            mdir, src, legacy = resolve_eval_mask_dir(
                ds_path, mask_subdir=args.mask_subdir,
                allow_legacy=bool(args.allow_legacy_mask))
        if mdir:
            idx = frozen_mask_index(mdir)
            if idx:
                mask_index, mask_source = idx, src
                mask_kind = "boolean" if not legacy else "legacy-class"
                mask_validity = "legacy" if legacy else "canonical"
                if legacy and src == "seg_mask":
                    if args.mask_class is None:
                        raise SystemExit(
                            "REFUSE: legacy seg_mask 需显式 --mask-class（VOC=15 vs ADE20K 0 起=12，"
                            "猜错即静默测错区域）。canonical 路径不需要类号：用 dynamic_mask/。")
                    mask_class = args.mask_class
        if mask_source:
            print(f"[render_compare] eval mask: source={mask_source} kind={mask_kind} "
                  f"class={mask_class} validity={mask_validity} ({len(mask_index)} stems)", flush=True)
        else:
            print("[render_compare] no frozen dynamic mask found -> static metrics skipped", flush=True)

    from utils.static_eval import static_background_metrics, vacated_contrast_metrics  # noqa: E402
    # ── 仪器护栏（--max-scale-m）：剔除退化巨基元，防栅格化器 numel 溢出 ──
    # 依据：crowd2 exit 图在部分相机下 int32 溢出（巨基元×瓦片数）；两臂同规则、剔除计数入报告。
    if float(args.max_scale_m) > 0:
        with torch.no_grad():
            _s = gaussians.get_scaling if hasattr(gaussians, "get_scaling") else None
            if _s is None:
                import numpy as _np
                _s = torch.exp(torch.as_tensor(
                    _np.stack([gaussians._scaling.detach().cpu().numpy()[:, i] for i in range(gaussians._scaling.shape[1])], 1)
                ))
            _big = _s.max(dim=1).values > float(args.max_scale_m)
            _n = int(_big.sum())
            print(f"[render_compare] scale guard >{args.max_scale_m}m: pruning {_n} degenerate primitives "
                  f"of {int(_big.numel())}", flush=True)
            if _n:
                gaussians._opacity.data[_big] = -20.0  # sigmoid≈0 ⇒ 栅格化前剔除
    from utils.eval_utils import _undistort_depth_like  # noqa: E402
    depth_paths = getattr(dataset, "depth_paths", None)
    color_paths = getattr(dataset, "color_paths", None)

    # 掩码关联：gtmc 以 depth stem 为键；部分序列的 seg_mask 以 RGB 时间戳为键。
    # 三级匹配：depth stem 精确 → RGB stem 精确 → 最近邻时间戳（≤50ms，与数据集关联阈值同量级）。
    import bisect as _bisect

    def _is_ts(s):
        try:
            float(s)
            return True
        except (TypeError, ValueError):
            return False

    mask_ts = sorted((float(k), v) for k, v in mask_index.items() if _is_ts(k))
    mask_ts_keys = [t for t, _ in mask_ts]

    def _nearest_mask_path(ts, tol=0.05):
        if not mask_ts_keys:
            return None
        i = _bisect.bisect_left(mask_ts_keys, ts)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(mask_ts_keys):
                d = abs(mask_ts_keys[j] - ts)
                if best is None or d < best[0]:
                    best = (d, mask_ts[j][1])
        if best is not None and best[0] <= tol:
            return best[1]
        return None

    n_dyn_missing = [0]  # 掩码未命中的渲染帧数（report 用）
    n_skip = [0]         # 渲染失败跳过的帧数（--skip-unrenderable）

    def frame_dynamic_mask(idx):
        """(H,W) bool dynamic mask for frame idx（三级匹配：depth stem → RGB stem → 最近邻 ts）。"""
        if not mask_index or depth_paths is None or idx >= len(depth_paths):
            return None
        stem = os.path.splitext(os.path.basename(depth_paths[idx]))[0]
        mpath = mask_index.get(stem)
        if mpath is None and color_paths is not None and idx < len(color_paths):
            mpath = mask_index.get(os.path.splitext(os.path.basename(color_paths[idx]))[0])
        if mpath is None and _is_ts(stem):
            mpath = _nearest_mask_path(float(stem), tol=0.05)
        if mpath is None:
            return None
        from utils.gtmc_mask import load_frozen_mask
        if mask_kind == "legacy-class":
            from PIL import Image as _Image
            return np.asarray(_Image.open(mpath).convert("L")) == mask_class
        return load_frozen_mask(mpath)   # 0/255 布尔：>127

    lpips_fn = LearnedPerceptualImagePatchSimilarity(net_type="alex", normalize=True).to(device)

    # 残影（vacated）指标需要"严格早于当前帧的所有掩码并集"——增量扫描一次（与运行期协议同构）
    all_ids = sorted(pose_by_id.keys())
    past_union = None
    union_ptr = 0
    recent_masks = (collections.deque(maxlen=int(args.vacated_window_frames))
                    if int(args.vacated_window_frames) > 0 else None)

    def rnd(v):
        """float -> round(4) or None（NaN/inf 归一为 None，JSON 可序列化）"""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)

    per_frame = []
    for idx in frame_ids:
        if idx not in pose_by_id:
            print(f"  frame {idx}: no pose, skip", flush=True)
            continue
        gt_image, gt_depth, _ = dataset[idx]
        if not torch.is_tensor(gt_image):
            gt_image = torch.as_tensor(gt_image, device=device)
        gt_image = gt_image.to(device).float()
        if gt_image.dim() == 3 and gt_image.shape[0] != 3:  # 容错：HWC
            gt_image = gt_image.permute(2, 0, 1)
        if gt_image.max() > 1.5:
            gt_image = gt_image / 255.0

        w2c = np.linalg.inv(pose_by_id[idx])
        # 先用 GT 位姿初始化 Camera（构造时 R/T 为单位阵；update_RT 写入估计位姿）
        # 注意：world_view_transform = getWorld2View2(R,T).T，与 run 内一致。
        cam_gt = None
        cam = Camera(
            uid=idx, color=None, depth=None,
            gt_T=torch.eye(4, device=device),
            projection_matrix=proj,
            fx=dataset.fx, fy=dataset.fy, cx=dataset.cx, cy=dataset.cy,
            fovx=dataset.fovx, fovy=dataset.fovy,
            image_height=H, image_width=W, device=args.device,
        )
        cam.update_RT(
            torch.as_tensor(w2c[:3, :3], dtype=torch.float32, device=device),
            torch.as_tensor(w2c[:3, 3], dtype=torch.float32, device=device),
        )

        with torch.no_grad():
            try:
                pkg = render(cam, gaussians, pipeline_params, background)
            except RuntimeError as _e:
                if args.skip_unrenderable:
                    n_skip[0] += 1
                    print(f"  frame {idx}: RENDER SKIPPED ({str(_e)[:60]})", flush=True)
                    continue
                raise
        if pkg is None:
            print(f"  frame {idx}: render returned None, skip", flush=True)
            continue
        rendering = torch.clamp(pkg["render"], 0.0, 1.0)
        depth_r = pkg["depth"]

        mask = gt_image > 0
        p = psnr(rendering[mask].unsqueeze(0), gt_image[mask].unsqueeze(0)).item()
        s = ssim(rendering.unsqueeze(0), gt_image.unsqueeze(0)).item()
        l = lpips_fn(rendering.unsqueeze(0), gt_image.unsqueeze(0)).item()
        d_l1 = _compute_depth_l1_cm(depth_r, gt_depth) if gt_depth is not None else None

        # ── 静态区/残影指标（掩码缺失时静默跳过；与运行期 P-A 协议同源）──
        sm, vm, fvm = None, None, None
        dyn = frame_dynamic_mask(idx) if mask_index else None
        if dyn is not None and gt_depth is not None:
            gt_depth_u = _undistort_depth_like(dataset, gt_depth)
            gt_depth_t = torch.as_tensor(np.asarray(gt_depth_u), device=device, dtype=torch.float32)
            dyn_t = torch.from_numpy(np.asarray(dyn, dtype=bool))
            sm = static_background_metrics(
                rendering, gt_image, depth_r.squeeze(), gt_depth_t,
                dynamic_mask=dyn_t,
                render_opacity=pkg.get("opacity"),
                d_max_cm=args.dmax_cm, a_eval=args.a_eval, lpips_fn=lpips_fn,
            )
            if not args.no_vacated:
                # 严格早于 idx 的所有帧掩码并入 past_union（每帧恰好处理一次）
                while union_ptr < len(all_ids) and all_ids[union_ptr] < idx:
                    j = all_ids[union_ptr]
                    union_ptr += 1
                    jm = frame_dynamic_mask(j)
                    if jm is not None:
                        jm_t = torch.from_numpy(np.asarray(jm, dtype=bool))
                        past_union = jm_t if past_union is None else (past_union | jm_t)
                        if recent_masks is not None:
                            recent_masks.append(jm_t)
                if past_union is not None:
                    vm = vacated_contrast_metrics(
                        rendering, gt_image, depth_r.squeeze(), gt_depth_t, dyn_t, past_union,
                        d_max_cm=args.dmax_cm,
                    )
                # FRESH-vacated（最近 N 帧窗口并集）：与运行期 static_freshvac_* 同构——
                # 跨批稳定口径（无界并集会长成全图、被背景项主导，见 verdict_L1 §2/§6）。
                if recent_masks:
                    recent_union = recent_masks[0]
                    for rm in list(recent_masks)[1:]:
                        recent_union = recent_union | rm
                    fvm = vacated_contrast_metrics(
                        rendering, gt_image, depth_r.squeeze(), gt_depth_t, dyn_t, recent_union,
                        d_max_cm=args.dmax_cm,
                    )

        # 拼图 [GT | render]（BGR 写 PNG；输入为 RGB 张量）
        gt_np = (gt_image.permute(1, 2, 0).detach().cpu().numpy() * 255).astype(np.uint8)
        rd_np = (rendering.permute(1, 2, 0).detach().cpu().numpy() * 255).astype(np.uint8)
        gt_bgr = cv2.cvtColor(gt_np, cv2.COLOR_RGB2BGR)
        rd_bgr = cv2.cvtColor(rd_np, cv2.COLOR_RGB2BGR)
        row = cv2.hconcat([gt_bgr, rd_bgr])
        cv2.putText(row, f"GT  |  render  PSNR={p:.2f}dB  SSIM={s:.3f}  frame={idx}",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(out_dir, f"cmp_f{idx:05d}.png"), row)
        if args.jpg:
            cv2.imwrite(os.path.join(out_dir, f"cmp_f{idx:05d}.jpg"), row,
                        [cv2.IMWRITE_JPEG_QUALITY, 88])

        # 深度可视化（归一化到帧内 1-99 分位，jet；有效性 <0 置灰）
        d = depth_r.squeeze().detach().cpu().numpy()
        dv = d[np.isfinite(d) & (d > 0.01)]
        if dv.size:
            lo, hi = np.percentile(dv, 1), np.percentile(dv, 99)
            dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        else:
            dn = np.zeros_like(d)
        dn = (dn * 255).astype(np.uint8)
        dn_col = cv2.applyColorMap(dn, cv2.COLORMAP_JET)
        if gt_depth is not None:
            gd = np.asarray(gt_depth, dtype=np.float32)
            gdv = gd[(gd > 0.01) & np.isfinite(gd)]
            if gdv.size:
                lo2, hi2 = np.percentile(gdv, 1), np.percentile(gdv, 99)
                gdn = (np.clip((gd - lo2) / max(hi2 - lo2, 1e-6), 0, 1) * 255).astype(np.uint8)
                gdn_col = cv2.applyColorMap(gdn, cv2.COLORMAP_JET)
                row2 = cv2.hconcat([gdn_col, dn_col])
            else:
                row2 = dn_col
        else:
            row2 = dn_col
        cv2.putText(row2, f"GT depth | render depth  L1={d_l1 if d_l1 is None else round(d_l1,1)}cm  frame={idx}",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(out_dir, f"depth_f{idx:05d}.png"), row2)

        rec = {"frame": idx, "psnr": round(p, 4), "ssim": round(s, 4),
               "lpips": round(l, 4), "depth_l1_cm": None if d_l1 is None else round(d_l1, 4)}
        if sm is not None:
            rec.update({
                "static_support_px": int(sm["static_support_px"]),
                "static_psnr": rnd(sm["static_psnr"]),
                "static_ssim": rnd(sm["static_ssim"]),
                "static_lpips": rnd(sm.get("static_lpips")),
                "static_coverage": rnd(sm["static_coverage"]),
                "static_depth_l1_pen_cm": rnd(sm["static_depth_l1_pen_cm"]),
            })
        if vm is not None:
            rec.update({
                "vacated_support_px": int(vm["vacated_support_px"]),
                "ghost_excess_depth_l1_cm": rnd(vm["ghost_excess_depth_l1_cm"]),
                "ghost_excess_psnr_db": rnd(vm["ghost_excess_psnr_db"]),
            })
        if fvm is not None:
            rec.update({
                "freshvac_support_px": int(fvm["vacated_support_px"]),
                "freshvac_ghost_excess_depth_l1_cm": rnd(fvm["ghost_excess_depth_l1_cm"]),
                "freshvac_ghost_excess_psnr_db": rnd(fvm["ghost_excess_psnr_db"]),
            })
        per_frame.append(rec)
        extra = ""
        if sm is not None:
            extra = (f" | static PSNR={rec['static_psnr']} SSIM={rec['static_ssim']}"
                     f" cov={rec['static_coverage']}")
            if vm is not None and rec.get("ghost_excess_depth_l1_cm") is not None:
                extra += f" | ghost_excess={rec['ghost_excess_depth_l1_cm']}cm"
        print(f"  frame {idx}: PSNR={p:.2f} SSIM={s:.3f} LPIPS={l:.3f} dL1={d_l1}{extra}", flush=True)

    if per_frame:
        def mean_of(key):
            vals = [r[key] for r in per_frame if r.get(key) is not None]
            return round(float(np.mean(vals)), 4) if vals else None

        out = {
            "run_dir": run_dir, "ply": ply_path, "trj": trj_path,
            "n_frames": len(per_frame), "interval": args.interval,
            "interval_note": "offline render; run-time eval_rendering interval=5 could collide with the KF grid (NaN root cause)",
            "mask_source": mask_source,
            "mask_kind": mask_kind,
            "mask_class": mask_class,
            "mask_validity": mask_validity,
            "mean_psnr": round(float(np.mean([r["psnr"] for r in per_frame])), 4),
            "mean_ssim": round(float(np.mean([r["ssim"] for r in per_frame])), 4),
            "mean_lpips": round(float(np.mean([r["lpips"] for r in per_frame])), 4),
            "mean_depth_l1_cm": (round(float(np.mean([r["depth_l1_cm"] for r in per_frame if r["depth_l1_cm"] is not None])), 4)
                                 if any(r["depth_l1_cm"] is not None for r in per_frame) else None),
            "per_frame": per_frame,
        }
        # 静态区/残影聚合（有掩码成功评分的帧才计入；None=无掩码/空支持集）
        if any("static_psnr" in r for r in per_frame):
            out["static_metrics_note"] = ("M_static = valid-gt-depth ∧ ¬dynamic (method-independent frozen mask); "
                                          "same functions as run-time P-A eval (utils/static_eval.py)")
            for k in ("static_psnr", "static_ssim", "static_lpips", "static_coverage",
                      "static_depth_l1_pen_cm"):
                out[f"mean_{k}"] = mean_of(k)
            out["mean_static_support_px"] = mean_of("static_support_px")
        if any("ghost_excess_depth_l1_cm" in r for r in per_frame):
            out["mean_ghost_excess_depth_l1_cm"] = mean_of("ghost_excess_depth_l1_cm")
            out["mean_ghost_excess_psnr_db"] = mean_of("ghost_excess_psnr_db")
        out["frames_render_skipped"] = int(n_skip[0])
        if any("freshvac_ghost_excess_depth_l1_cm" in r for r in per_frame):
            out["mean_freshvac_ghost_excess_depth_l1_cm"] = mean_of("freshvac_ghost_excess_depth_l1_cm")
            out["mean_freshvac_ghost_excess_psnr_db"] = mean_of("freshvac_ghost_excess_psnr_db")
            out["vacated_window_frames"] = int(args.vacated_window_frames)
            out["mean_vacated_support_px"] = mean_of("vacated_support_px")
        json.dump(out, open(os.path.join(out_dir, "render_metrics.json"), "w"), indent=1)
        msg = f"[render_compare] wrote {out_dir}  mean PSNR={out['mean_psnr']} SSIM={out['mean_ssim']} LPIPS={out['mean_lpips']}"
        if out.get("mean_static_psnr") is not None:
            msg += f" | static PSNR={out['mean_static_psnr']} cov={out.get('mean_static_coverage')}"
        if out.get("mean_ghost_excess_depth_l1_cm") is not None:
            msg += f" | ghost_excess={out['mean_ghost_excess_depth_l1_cm']}cm"
        if out.get("mean_freshvac_ghost_excess_depth_l1_cm") is not None:
            msg += (f" | freshvac_excess(w={out['vacated_window_frames']})="
                    f"{out['mean_freshvac_ghost_excess_depth_l1_cm']}cm")
        print(msg, flush=True)
    else:
        print("[render_compare] WARNING: no frames rendered", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
