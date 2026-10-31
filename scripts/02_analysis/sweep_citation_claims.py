#!/usr/bin/env python
"""类扫（可复跑）：扫描"跨文件错误引证"这一类残留（起因 = 2026-09-25 关卡① 致命-1）。

违规形状 = 声称某文件含某措辞，而该文件实际不含（引证不存在）。
本工具当前检查的**已知实例**：`存在性形态未试` 被挂在 `verdict_L1f_obsdebt.md` §0/§4 下
（实数：该文件 0 命中；原产地 = 一页纸 :25；已加更正指针）。

机制：
  1. **逐实例正向核验**：对每个 (措辞, 声称的宿主文件) 对，直接 grep 宿主文件——
     宿主不含该措辞 ⇒ 该引证处必须带更正标记，否则 UNMARKED。
  2. **块感知**：更正指针常写在下一行（本仓惯例），故对每个命中行检查其后 3 行的窗口。
  3. **负对照**：把已知的旧版违规文本喂给同一判定函数，必须变红（门可红的证据）。

用法：python scripts/02_analysis/sweep_citation_claims.py [--selftest]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 实例表：(措辞, 声称的宿主文件, 说明)
CLAIMS = [
    ("存在性形态未试", "results/lifecycle_paper2/evidence/verdict_L1f_obsdebt.md",
     "L1f 判决 §0/§4 据称含此措辞（实数 0 命中；原产地 = 一页纸）"),
    # 2026-09-25 关卡① v2 审查新增（同型：把事实挂到不含它的文件上）
    ("15/17", "results/lifecycle_paper2/evidence/verdict_instrument_v2.md",
     "balloon2 m3 可用帧 15/17 据称在 verdict_instrument_v2（实数 0 命中；实在 onepager_table）"),
    ("across_seed_iqr", "results/lifecycle_paper2/evidence/l1f_obsdebt_manifest.json",
     "据称在 robustness_diagnostic 下（实数该键不在该节；实在 main_criterion.primary）"),
    # 2026-09-27 关卡① G4 遗留（F6 类：引用**非卡外部来源**当语料占位者）——
    # 新实例进表即"该类可被机器检出"；行内须标"非卡来源"（MARKERS 已含）才算已登记。
    ("DOGL-SLAM", "resources/lit_dyn_mapping/",
     "RA-L'26 由 2026-09-27 web 检索引入、语料无该卡 ⇒ 引用处须标「非卡来源」"),
]

# 更正标记词（出现即视为"已登记更正"，不算残留）
# 收紧（关卡① v2 审查：裸词"引证/已改"可自掩蔽——注入"…（以上为该判决的引证）"会被误放行）
MARKERS = re.compile("更正|原产地|不成立|不在该文件|原文保留|已撤回|疑为错引|引证有误|非卡来源")

# **"必须标记"表（2026-09-27 新增；E2 在线 G1 重大-6 的机制化）**：这些措辞**无论宿主 basename 是否同行出现**，
# 只要在任何 .md 里被引用，同一窗口必须有 MARKERS 之一（典型 = 非卡外部来源）。
# 依据：原实现（CLAIMS）要求"宿主 basename 同行/邻行出现"才判红 ⇒ 单独提一句非卡来源（不点宿主名）会逃逸，
# 产生 UNMARKED=0 的**假绿**（2026-09-27 实测：`prereg_E2_online.md` v1 的 DOGL-SLAM 未被扫出）。
REQUIRE_MARKER = [
    ("DOGL-SLAM", "语料 `resources/lit_dyn_mapping/` 无该卡（RA-L'26 web 检索引入）⇒ 任何 .md 引用处须标「非卡来源」"),
]

# **说明性载体**（只描述该错误、不据以支持结论）：本角色的定义文件与工具自身。
# 依据：2026-09-25 首次实跑，slam-critic.md 的 P38 定义行（举例说明"引证错宿主"）被误判——
# 定义文件里出现该组合是**在讲这个错误**，不是在犯这个错误。豁免面须最小（仅这两个路径）。
DESCRIPTIVE_CARRIERS = (
    ".zcode/agents/slam-critic.md",
    "scripts/02_analysis/sweep_citation_claims.py",
)


def _ls_md(pattern: str = "*.md") -> list[str]:
    """`git ls-files` 的路径列表，**强制关闭 core.quotepath**。

    默认 `core.quotepath=true` 会把非 ASCII 路径转义成 `"biyelunwen/...\\350\\256..."`
    （带引号 + 八进制），`Path` 打不开 ⇒ 整条 sweep 抛 FileNotFoundError（2026-10-31 实测：
    仓内 `biyelunwen/02_resources/论文作者以及其他信息.md` 一条就足以让本门永久崩）。
    门崩掉比门变红更危险：G4 要求"程序化门先行"，而崩掉的门外表是"没跑过"。
    """
    return subprocess.check_output(
        ["git", "-c", "core.quotepath=false", "ls-files", pattern],
        cwd=REPO, text=True).split()


def host_contains(phrase: str, host: str) -> bool:
    f = REPO / host
    if not f.exists():
        return False
    if f.is_dir():
        # 目录宿主（F6 类：引用"非卡外部来源"当语料占位者）——语义 = 整个语料是否含该措辞。
        # 依据：2026-09-27 关卡① G4 遗留项（DOGL-SLAM 无卡却被当占位者）。
        return any(phrase in (REPO / r).read_text(errors="ignore")
                   for r in _ls_md(f"{host}*.md"))
    return phrase in f.read_text(errors="ignore")


def is_marked_window(lines: list[str], i: int, window: int = 3) -> bool:
    return any(MARKERS.search(lines[j]) for j in range(i, min(i + window, len(lines))))


def scan_text(text: str, host_contains_phrase: bool) -> list[str]:
    """返回该文本中"未带更正标记的违规引证"行清单（纯函数，供负对照）。"""
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        for phrase, host, _desc in CLAIMS:
            if phrase not in line:
                # 折行容忍：措辞在本行、文件名在后一行（或反之）
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if not (phrase in nxt and f"{Path(host).name}" in line):
                    continue
            elif f"{Path(host).name}" not in line:
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if f"{Path(host).name}" not in nxt:
                    continue
            if not host_contains_phrase and not is_marked_window(lines, i):
                out.append(f"UNMARKED:{i + 1}: {line.strip()[:110]}")
    return out


def scan_require_marker(text: str) -> list[str]:
    """"必须标记"措辞的未标记行清单（纯函数，供负对照）。

    与 `scan_text` 的差别：**不要求宿主 basename 同行** ⇒ 任何 .md 里出现该措辞即须带 MARKERS。
    """
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        for phrase, _desc in REQUIRE_MARKER:
            if phrase in line and not is_marked_window(lines, i):
                out.append(f"UNMARKED:{i + 1}: {line.strip()[:110]}")
    return out


def sweep() -> int:
    hits = []
    for phrase, host, desc in CLAIMS:
        present = host_contains(phrase, host)
        print(f"[claim] '{phrase}' in {host} => {'PRESENT' if present else 'ABSENT(0 命中)'}  ({desc})")
        if present:
            continue  # 宿主确实含该措辞 ⇒ 引证成立，无需标记
        files = _ls_md()
        for rel in files:
            if "DECISIONS_ARCHIVE" in rel:
                continue  # 归档只读，不追改
            if rel in DESCRIPTIVE_CARRIERS:
                continue  # 说明性载体（定义工具本体）
            f = REPO / rel
            hits += [f"{rel} {h}" for h in scan_text(f.read_text(errors="ignore"), present)]
    # "必须标记"表：与宿主无关，任何 .md 引用即须带标记（E2 在线 G1 重大-6 的机制化）
    files = _ls_md()
    for rel in files:
        if "DECISIONS_ARCHIVE" in rel or rel in DESCRIPTIVE_CARRIERS:
            continue
        hits += [f"{rel} {h}" for h in scan_require_marker((REPO / rel).read_text(errors="ignore"))]
    for h in hits:
        print(h)
    print(f"UNMARKED = {len(hits)}")
    return 1 if hits else 0


def selftest() -> int:
    """负对照：旧版未标记的违规文本必须被判红；带标记的更正块必须放行。"""
    old_bad = '| D2-016 | ... | `verdict_L1f_obsdebt.md` §0/§4（资源形态证伪、存在性形态未试） |'
    marked = '3. **资源形态已证伪、存在性形态未试**（`verdict_L1f_obsdebt.md` §0/§4）：\n' \
             '   **⚠ 2026-09-25 更正（关卡① 致命-1）：该引证不成立——措辞不在该文件**'
    bad_hits = scan_text(old_bad, host_contains_phrase=False)
    ok_hits = scan_text(marked, host_contains_phrase=False)
    assert bad_hits, "负对照失败：未标记的旧引证未被抓到 ⇒ 门失效"
    assert not ok_hits, f"正对照失败：带更正标记的块被误判 ⇒ 过度报警 {ok_hits}"
    # 宿主真的含该措辞时（假设性），引证成立 ⇒ 不判红
    assert not scan_text(old_bad, host_contains_phrase=True), "宿主含措辞时不应判红"
    # 说明性载体豁免须**最小**：证明豁免清单只含定义工具本体（防日后被滥用扩大）
    assert set(DESCRIPTIVE_CARRIERS) == {".zcode/agents/slam-critic.md",
                                         "scripts/02_analysis/sweep_citation_claims.py"}, \
        "说明性载体清单被扩大 —— 豁免面过宽等于门失效"
    # "必须标记"表的负对照（E2 在线 G1 重大-6）：裸引用须变红，带「非卡来源」须放行；
    # 且**不依赖宿主 basename 同行**（这正是原实现的假绿来源）。
    bare = "**禁**「首个对象级动态 SLAM」（DOGL-SLAM RA-L'26 近占）；我们 = 对象级 + 自持跟踪"
    marked2 = "**禁**「首个对象级动态 SLAM」（**DOGL-SLAM RA-L'26 近占；⚠ 非卡来源**）；我们 = 对象级 + 自持跟踪"
    assert scan_require_marker(bare), "负对照失败：裸引用未带「非卡来源」未被抓到 ⇒ 该类门失效"
    assert not scan_require_marker(marked2), f"正对照失败：带「非卡来源」被误判 {scan_require_marker(marked2)}"
    assert REQUIRE_MARKER, "必须标记表为空 —— 机制被摘除"
    # 路径编码负对照（2026-10-31）：`git ls-files` 的默认 quotepath 会把非 ASCII 路径
    # 转义成带引号的八进制串，Path 打不开 ⇒ 本门整体崩（不是变红）。断言枚举出的
    # 每个 .md 都能被 Path 打开，且确实覆盖到仓内非 ASCII 路径。
    paths = _ls_md()
    assert paths, "git ls-files 返回空 —— 门没在扫任何文件"
    bad = [p for p in paths if not (REPO / p).is_file()]
    assert not bad, f"ls-files 路径无法解析（quotepath 未关？）: {bad[:3]}"
    assert any(any(ord(ch) > 127 for ch in p) for p in paths), \
        "语料里已无非 ASCII 路径 —— 该负对照失去意义，请更新本断言"
    print("selftest OK（负对照变红 / 更正块放行 / 宿主含措辞时放行 / 说明性载体最小 / "
          "必须标记表两态 / 非 ASCII 路径可解析）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    return selftest() if args.selftest else sweep()


if __name__ == "__main__":
    sys.exit(main())
