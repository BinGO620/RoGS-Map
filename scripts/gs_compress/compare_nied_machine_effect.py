#!/usr/bin/env python
"""compare_nied_machine_effect.py — 量化 Niedermayr QAT 压缩的**跨机效应**。

背景（2026-10-16，exp52）：远程 3090 与本机 2060 都跑过 Niedermayr c3dgs 基线。
本机全量重跑后，凡是"远程独立压过、本机又独立压了一遍"的地图，就是一对天然对照，
可直接量出「同一张冻结地图、同代码同迭代数，换一张卡」对 npz 字节数与渲染质量的影响。

**有效对照的判定（关键，别数错）**：远程那 48 行里有 12 张（balloon/balloon2 系列）的 npz 是
从本机 rsync 过去的、远程只是**复用**（远程日志 `复用已有 npz`）⇒ 字节相同是必然，**不算对照**。
这 12 张的 tag 清单就存在 `rd/superseded/learned_nied_L2_local_stopped_at_12.json`（本机停跑时的 12 行）。

输出：results/gs_compress/evidence/learned_nied_machine_effect_2026-10-16.md（人读）+ 同目录 .json（机读）

用法：/data/conda_envs/monogs-ours/bin/python scripts/gs_compress/compare_nied_machine_effect.py
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RD = REPO / "results/gs_compress/evidence/rd"
EV = REPO / "results/gs_compress/evidence"
REMOTE = RD / "partial_remote3090"
SUPERSEDED = RD / "superseded/learned_nied_L2_local_stopped_at_12.json"


def rows(p: Path):
    return {r["tag"]: r for r in json.loads(p.read_text())["rows"]}


def main():
    rsync_tags = set(rows(SUPERSEDED))  # 12 张被 rsync 复用 ⇒ 非独立对照
    pairs = []
    for split in ("L2", "L3"):
        rem_p, loc_p = REMOTE / f"learned_nied_{split}.json", RD / f"learned_nied_{split}.json"
        if not (rem_p.exists() and loc_p.exists()):
            print(f"跳过 {split}：缺 {rem_p if not rem_p.exists() else loc_p}")
            continue
        rem, loc = rows(rem_p), rows(loc_p)
        for t in sorted(set(rem) & set(loc)):
            if t in rsync_tags:
                continue
            a, b = rem[t], loc[t]
            pa = (a.get("render") or {}).get("mean_psnr")
            pb = (b.get("render") or {}).get("mean_psnr")
            pairs.append({
                "split": split, "tag": t,
                "npz_remote": a["npz_bytes"], "npz_local": b["npz_bytes"],
                "dnpz": b["npz_bytes"] - a["npz_bytes"],
                "dratio": b["ratio_full"] - a["ratio_full"],
                "psnr_remote": pa, "psnr_local": pb,
                "dpsnr": (pb - pa) if (pa is not None and pb is not None) else None,
            })

    if not pairs:
        print("没有有效对照对（本机全量尚未跑到远程压过的地图）")
        return

    n = len(pairs)
    byte_same = sum(1 for p in pairs if p["dnpz"] == 0)
    dr = [abs(p["dratio"]) for p in pairs]
    dp = [abs(p["dpsnr"]) for p in pairs if p["dpsnr"] is not None]
    sdr = [p["dratio"] for p in pairs]
    sdp = [p["dpsnr"] for p in pairs if p["dpsnr"] is not None]

    L = [
        "# Niedermayr c3dgs 压缩步骤的跨机效应（实测，2026-10-16 exp52）",
        "",
        "对照定义：同一张冻结地图、同一份代码、同为 `--iters 5000`，分别在远程 3090 与本机 2060",
        "各**独立**压一遍。已剔除 12 张「npz 从本机 rsync 过去、远程只复用」的伪对照",
        "（见 `rd/superseded/learned_nied_L2_local_stopped_at_12.json`）。",
        "",
        f"- 有效对照地图数 **n = {n}**（L2 {sum(1 for p in pairs if p['split'] == 'L2')}"
        f" / L3 {sum(1 for p in pairs if p['split'] == 'L3')}）",
        f"- npz 字节完全相同的地图：**{byte_same}/{n}**",
        "",
        "| 量 | 均值 | 中位数 | 极差(绝对) |",
        "|---|---|---|---|",
        f"| Δnpz (字节) | {st.mean([p['dnpz'] for p in pairs]):+.1f} | "
        f"{st.median([p['dnpz'] for p in pairs]):+.1f} | {max(abs(p['dnpz']) for p in pairs)} |",
        f"| Δratio | {st.mean(sdr):+.3e} | {st.median(sdr):+.3e} | {max(dr):.3e} |",
        f"| ΔPSNR (dB) | {st.mean(sdp):+.4f} | {st.median(sdp):+.4f} | {max(dp):.4f} |",
        "",
        "| split | tag | npz 3090 | npz 2060 | Δnpz | Δratio | PSNR 3090 | PSNR 2060 | ΔPSNR |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in pairs:
        L.append(f"| {p['split']} | {p['tag']} | {p['npz_remote']} | {p['npz_local']} | "
                 f"{p['dnpz']:+d} | {p['dratio']:+.3e} | {p['psnr_remote']:.4f} | "
                 f"{p['psnr_local']:.4f} | {p['dpsnr']:+.4f} |")
    L += [
        "",
        "## 怎么读这张表（**别把它读成「机器效应」**）",
        "",
        "该 submodule **没有任何随机种子**：`finetune.py` 用 `randint` 随机采样相机、`Scene(shuffle=True)`",
        "用 `random.shuffle`，全仓无 `--seed` / `torch.manual_seed` / `random.seed` / `np.random.seed`。",
        "因此本表的每一对是**两次独立运行**的差，里面**混着**「机器不同」与「方法自身的跑间随机性」，",
        "本表**无法**把两者分开。要分解，必须补同机重复：见 `measure_nied_repeat_noise.sh`",
        "（同机、同代码、同迭代数再压一遍 ⇒ 纯跑间地板），把两个量级一比才有结论。",
        "",
        "**已经成立的结论（与归因无关）**：该 learned 基线的数字**不是单次运行可复现的**——",
        "同一张冻结地图跑两遍就会变（本表 n 对全部不同，npz 字节无一相同）。",
        "所以：(1) 不能把不同来源的运行结果混进同一个均值；(2) 表里这一行本质是一个**随机样本**，",
        "若跑间地板不可忽略，须在题注/正文登记方差或改为多种子。",
        "",
        "（对照：SOG 那一行是 post-hoc、无训练的确定性前向压缩，无随机性，不受此影响。）",
    ]
    out_md = EV / "learned_nied_machine_effect_2026-10-16.md"
    out_md.write_text("\n".join(L) + "\n")
    (EV / "learned_nied_machine_effect_2026-10-16.json").write_text(json.dumps({
        "n_pairs": n, "byte_identical": byte_same,
        "mean_dnpz": st.mean([p["dnpz"] for p in pairs]),
        "mean_dratio": st.mean(sdr), "max_abs_dratio": max(dr),
        "mean_dpsnr": st.mean(sdp), "max_abs_dpsnr": max(dp),
        "pairs": pairs,
    }, indent=2))
    print(f"n={n}  byte-identical={byte_same}/{n}  "
          f"mean Δratio={st.mean(sdr):+.3e} (max {max(dr):.3e})  "
          f"mean ΔPSNR={st.mean(sdp):+.4f} dB (max {max(dp):.4f})")
    print("wrote", out_md)


if __name__ == "__main__":
    main()
