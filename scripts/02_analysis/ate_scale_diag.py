"""ATE 残差成分诊断（用户 2026-09-25 观察：对齐后 est/GT 两线平行不重合，疑尺度）。

归档说明（2026-09-25，用户拍板"归档"）：本脚本由 /tmp 移入仓内共享分析目录；
起因/方法/结论 = results/paper2_fulltable/evidence/ate_scale_diag_2026-09-25.md；
图与 diag.json = 同目录 ate_scale_diag_figs/。

判定性检验：同一 run 分别做 SE3 Umeyama（correct_scale=False，= 房式主口径）与
Sim3 Umeyama（把尺度放出来）。若 Sim3 后误差塌掉且叠图重合 ⇒ 残差由尺度主导；
若不塌 ⇒ 残差是形状畸变/漂移，不是（纯）尺度。正对照：SE3 RMSE 必须与
tracking_raw.csv 的 ate_rmse_cm 逐位一致（同 evo 同实现）。
输出：/tmp/ate_scale_diag/diag.json + 每个 run 两张叠图（se3/sim3）。
"""
import json
import os
import numpy as np
from evo.core import metrics, geometry, trajectory
from evo.core.trajectory import PosePath3D

RUNS = {
    "balloon2_L3off_s0": "results/lifecycle_paper2/L3_balloon2_off_s0",
    "balloon_L3off_s0": "results/lifecycle_paper2/L3_balloon_off_s0",
    "pt_L3off_s0": "results/lifecycle_paper2/L3_person_tracking_off_s0",
    "pt2_L3off_s0": "results/lifecycle_paper2/L3_person_tracking2_off_s0",
    "mvnobox_L3off_s0": "results/lifecycle_paper2/L3_mvnobox_off_s0",
    "crowd2_L3off_s0": "results/lifecycle_paper2/L3_crowd2_off_s0",
    # ate_census 族 2026-10-10 归档（Step3c）⇒ 逻辑路径仍写 results/，由 resolve_run() 兜底解析
    "pt_atecensus_s1": "results/ate_census/person_tracking_seed1/datasets_bonn/person_tracking/seed_1/2026-09-03-12-02-35",
    "balloon2_r33gate_s1": "results/paper2_fulltable/r33_rebase_gate_balloon2_seed1/datasets_bonn/r33_rebase_gate_balloon2/seed_1/2026-09-16-04-24-10",
}

# 归档镜像兜底（2026-10-11）：已关闭族四件套移入 archive/closed_families/<族>/ 后，
# 逻辑路径 results/<族>/… 在活区不存在 ⇒ 解析到归档副本（内容未改，诊断语义不变）。
ARCHIVE_MIRROR = "archive/closed_families"


def resolve_run(rel):
    """逻辑 run 路径 → 实际路径：活区优先，否则按归档镜像解析；两者皆无则原样返回（由 find_trj 报错）。"""
    if os.path.isdir(rel):
        return rel
    parts = rel.split("/", 2)
    if len(parts) == 3 and parts[0] == "results":
        cand = os.path.join(ARCHIVE_MIRROR, parts[1], "results", parts[2])
        if os.path.isdir(cand):
            return cand
    return rel


def find_trj(run_dir):
    for root, _, fs in os.walk(run_dir):
        if "trj_full_final.json" in fs:
            return os.path.join(root, "trj_full_final.json")
    raise FileNotFoundError(run_dir)


def rot_angle_deg(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1, 1))))


def ape_rmse(P_est, P_gt):
    def path(P):
        poses = [np.eye(4) for _ in range(len(P))]
        for i, p in enumerate(P):
            poses[i][:3, 3] = p
        return PosePath3D(poses_se3=poses)

    m = metrics.APE(metrics.PoseRelation.translation_part)
    m.process_data((path(P_gt), path(P_est)))
    stats = m.get_all_statistics()
    return stats, m


def path_len(P):
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


def main():
    out_dir = "/tmp/ate_scale_diag"
    os.makedirs(out_dir, exist_ok=True)
    from evo.tools import plot as evo_plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = []
    for name, rd in RUNS.items():
        rd = resolve_run(rd)
        p = find_trj(rd)
        with open(p) as f:
            d = json.load(f)
        P_est = np.array([np.asarray(T)[:3, 3] for T in d["trj_est"]])
        P_gt = np.array([np.asarray(T)[:3, 3] for T in d["trj_gt"]])

        # SE3 (house convention: no scale) — same umeyama the house eval uses
        R, t, _ = geometry.umeyama_alignment(P_est.T, P_gt.T, with_scale=False)
        E_se3 = (R @ P_est.T).T + t
        se3_stats, se3_metric = ape_rmse(E_se3, P_gt)
        # Sim3 (scale free)
        R3, t3, s3 = geometry.umeyama_alignment(P_est.T, P_gt.T, with_scale=True)
        E_sim3 = s3 * (R3 @ P_est.T).T + t3
        sim3_stats, _ = ape_rmse(E_sim3, P_gt)

        len_est, len_gt = path_len(P_est), path_len(P_gt)
        # positive control vs tracking_raw.csv
        rec = None
        csv_p = None
        for root, _, fs in os.walk(rd):
            if "tracking_raw.csv" in fs:
                csv_p = os.path.join(root, "tracking_raw.csv")
                break
        if csv_p:
            import csv as _csv
            with open(csv_p) as f:
                rec = next(_csv.DictReader(f)).get("ate_rmse_cm")

        row = {
            "run": name,
            "n": len(P_est),
            "ate_se3_cm": round(se3_stats["rmse"] * 100, 3),
            "ate_sim3_cm": round(sim3_stats["rmse"] * 100, 3),
            "collapse_pct": round(100 * (1 - sim3_stats["rmse"] / se3_stats["rmse"]), 1),
            "scale_sim3": round(float(s3), 5),
            "path_ratio_est_over_gt": round(len_est / len_gt, 5),
            "rot_deg_se3": round(rot_angle_deg(R), 2),
            "recorded_ate_cm": rec,
        }
        rows.append(row)

        # two overlay plots
        for tag, E, ttl in (
            ("se3", E_se3, f"SE3 aligned (house)  RMSE={se3_stats['rmse']*100:.2f}cm"),
            ("sim3", E_sim3, f"Sim3 aligned (s={float(s3):.4f})  RMSE={sim3_stats['rmse']*100:.2f}cm"),
        ):
            fig = plt.figure(figsize=(6, 5))
            ax = evo_plot.prepare_axis(fig, evo_plot.PlotMode.xy)
            ax.set_title(f"{name}\n{ttl}", fontsize=9)
            ax.plot(P_gt[:, 0], P_gt[:, 1], "--", color="gray", label="gt")
            ax.plot(E[:, 0], E[:, 1], "-", color="tab:red", lw=1.2, label="est (aligned)")
            ax.legend()
            fig.savefig(os.path.join(out_dir, f"{name}_{tag}.png"), dpi=110)
            plt.close(fig)

    out = os.path.join(out_dir, "diag.json")
    with open(out, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    hdr = f"{'run':24s} {'ATE_se3':>8s} {'ATE_sim3':>8s} {'塌缩%':>6s} {'s_sim3':>8s} {'path比':>8s} {'rot°':>7s} {'表值':>8s}"
    print(hdr)
    for r in rows:
        print(
            f"{r['run']:24s} {r['ate_se3_cm']:8.2f} {r['ate_sim3_cm']:8.2f} "
            f"{r['collapse_pct']:6.1f} {r['scale_sim3']:8.4f} "
            f"{r['path_ratio_est_over_gt']:8.4f} {r['rot_deg_se3']:7.1f} "
            f"{str(r['recorded_ate_cm']):>8s}"
        )
    print("json:", out)


if __name__ == "__main__":
    main()
