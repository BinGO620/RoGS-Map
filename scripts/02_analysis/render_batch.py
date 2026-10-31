#!/usr/bin/env python
"""render_batch.py — R34 后处理·过夜批：离线渲染对比图 + (可选) Bonn 官方几何评估。

读一个 run 列表文件（每行 `<run_dir_glob> [geom]`），对每个 run：
  1. 调 scripts/02_analysis/render_compare.py（GT|render 对比图 + 渲染指标，--jpg）
  2. 若带 `geom` 标记：调 utils.geometry_metrics.evaluate_run_geometry
     （TSDF mesh + 官方 Bonn 协议 accuracy/completion/F@5cm；GT 点云=T_g 变换）

只读 run 的既有产物（PLY/轨迹/config）；新文件写入
`results/{exp_id}/render_compare/<run>_<ts>/` 与 run_dir/geometry/、mapping_geometry_metrics_v2.json
（均为 eval 管线标准产物，不改既有文件；D3 合规）。

用法（远程，仓库根目录）：
  PY=/home/jiangwenheng/anaconda3/envs/monogs-ours-3090/bin/python
  $PY scripts/02_analysis/render_batch.py --list scripts/02_analysis/render_batch_list_r1.txt \
      > /home/jiangwenheng/render_batch_r1.out 2>&1
完成标志：输出末尾 `BATCH_DONE <n>`；摘要落 `render_batch_summary.json`（cwd）。
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--max-frames", type=int, default=8)
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--geom-stride", type=int, default=5, help="几何 TSDF 积分步长")
    ap.add_argument("--out", default="/tmp/render_batch_summary.json")
    args = ap.parse_args()

    py = sys.executable
    entries = []
    for raw in open(args.list):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        entries.append((parts[0], "geom" in parts[1:]))

    results = []
    for i, (pattern, do_geom) in enumerate(entries):
        hits = sorted(glob.glob(pattern))
        if not hits:
            rec = {"pattern": pattern, "error": "no match"}
            results.append(rec)
            print(f"[{i+1}/{len(entries)}] NO_MATCH {pattern}", flush=True)
            continue
        run_dir = hits[-1]

        # 1) 渲染对比
        cmd = [py, "scripts/02_analysis/render_compare.py", "--run-dir", run_dir,
               "--max-frames", str(args.max_frames), "--interval", str(args.interval), "--jpg"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        rec = {"run_dir": run_dir, "render_rc": r.returncode}
        print(f"[{i+1}/{len(entries)}] RENDER rc={r.returncode} {run_dir}", flush=True)
        if r.returncode != 0:
            rec["render_err"] = (r.stderr or "")[-600:]
            print("  render_err:", rec["render_err"][-200:], flush=True)
        else:
            # 从 stdout 抓 mean 行
            for line in r.stdout.splitlines():
                if "mean PSNR" in line:
                    rec["render_mean"] = line.strip()
                    print("  " + line.strip(), flush=True)

        # 2) 几何（Bonn 官方协议）
        if do_geom:
            drv = (
                "import json,sys;sys.path.insert(0,'.');"
                "from utils.geometry_metrics import evaluate_run_geometry;"
                f"m=evaluate_run_geometry({run_dir!r}, frame_stride={args.geom_stride});"
                "print('GEOM_OK', json.dumps({k:m.get(k) for k in "
                "('accuracy_cm','completion_cm','completion_ratio','precision_ratio',"
                "'fscore','protocol_eligible','pose_source','mesh_faces')}, ensure_ascii=False))"
            )
            r2 = subprocess.run([py, "-c", drv], capture_output=True, text=True)
            rec["geom_rc"] = r2.returncode
            print(f"  GEOM rc={r2.returncode}", flush=True)
            if r2.returncode == 0:
                for line in r2.stdout.splitlines():
                    if line.startswith("GEOM_OK"):
                        rec["geom"] = json.loads(line[len("GEOM_OK"):].strip())
                        print("  " + line.strip()[:300], flush=True)
            else:
                rec["geom_err"] = (r2.stderr or "")[-600:]
                print("  geom_err:", rec["geom_err"][-200:], flush=True)

        results.append(rec)
        Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False))

    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"BATCH_DONE {len(results)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
