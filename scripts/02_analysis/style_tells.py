#!/usr/bin/env python
"""style_tells.py — 英文论文"去 AI 味"写作体检（可复跑判据脚本）。

依 2026-10-05 网络核查（Pangram 9 signs / Editage / EffortlessAcademic）+ 本仓叙事纪律，
量化以下 AI 写作特征（每项给计数 + 密度，非阈值判定；供人工整改）：

  em_dash      破折号密度（AI ~10× 人类；人类 ~2/10k 词）
  triad        三项并列（"A, B, and C" / "X, Y and Z" 型）——AI 4×
  not_only     "not only ... but also" / "not X but Y" 反转结构
  ai_phrase    高频 AI 短语（delve/it is worth noting/crucially/notably/moreover…）
  colon        冒号密度
  paren        括号密度
  bullet       分点/列举密度
  sent_cv      句长变异系数（AI 偏低=句子过于均匀；人类 >0.4 常见）
  passive      被动语态 rough 估计（"is/are/was/were + pp"）

用法：
  python scripts/02_analysis/style_tells.py papers/paper2/paper2_cvm.tex [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

AI_PHRASES = [
    "delve", "it is worth noting", "it is important to note", "crucially",
    "notably", "moreover", "furthermore", "in addition", "additionally",
    "significantly", "remarkably", "importantly", "ultimately",
    "it should be noted", "a testament to", "underscores", "highlights the",
    "plays a crucial role", "paves the way", "in the realm of", "when it comes to",
    "at the end of the day", "needless to say",
]


def strip_latex(s: str) -> str:
    s = re.sub(r"(?<!\\)%.*", "", s)                 # comments
    s = re.sub(r"\\(cite|ref|label|input|includegraphics)\{[^}]*\}", " ", s)
    s = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", s)
    s = re.sub(r"[{}$&~^_]", " ", s)
    return s


def sentences(text: str) -> list[str]:
    # rough: split on . ! ? followed by whitespace+capital, ignoring decimals
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def analyze(path: str) -> dict:
    raw = Path(path).read_text()
    body = strip_latex(raw)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", body)
    n_w = max(1, len(words))
    per10k = lambda c: round(c / n_w * 10000, 1)

    em = body.count("---") + body.count("—") + body.count(" -- ")
    # triad: three commas-joined items ending in ", and X" preceded by two ", "
    triads = len(re.findall(r"\b\w+,\s+\w+,\s+(?:and|or)\s+\w+", body))
    not_only = len(re.findall(r"\bnot only\b|\bnot\s+\w+\s+but\b|\brather than\b", body, re.I))
    ai_hits = {}
    for p in AI_PHRASES:
        c = len(re.findall(re.escape(p), body, re.I))
        if c:
            ai_hits[p] = c
    colon = body.count(":")
    paren = body.count("(") + body.count(")")
    bullets = len(re.findall(r"\\item\b", raw))
    sents = sentences(body)
    lens = [len(s.split()) for s in sents]
    cv = round(statistics.pstdev(lens) / max(1, statistics.mean(lens)), 3) if len(lens) > 3 else None
    passive = len(re.findall(r"\b(is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", body, re.I))

    return {
        "file": path, "words": n_w, "sentences": len(sents),
        "em_dash": {"count": em, "per10k": per10k(em)},
        "triad": {"count": triads, "per10k": per10k(triads)},
        "not_only_rather_than": {"count": not_only, "per10k": per10k(not_only)},
        "ai_phrases": ai_hits,
        "colon": {"count": colon, "per10k": per10k(colon)},
        "paren": {"count": paren, "per10k": per10k(paren)},
        "bullets": bullets,
        "sent_len_cv": cv,
        "passive_rough": {"count": passive, "per10k": per10k(passive)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = analyze(args.path)
    if args.json:
        print(json.dumps(r, indent=2)); return
    print(f"# style tells: {r['file']}  ({r['words']} words, {r['sentences']} sentences)")
    print(f"  em dash        : {r['em_dash']['count']:4d}  ({r['em_dash']['per10k']}/10k)   [human ~2, AI ~17]")
    print(f"  triads         : {r['triad']['count']:4d}  ({r['triad']['per10k']}/10k)   [AI 4x]")
    print(f"  not-only/rather: {r['not_only_rather_than']['count']:4d}  ({r['not_only_rather_than']['per10k']}/10k)")
    print(f"  colon          : {r['colon']['count']:4d}  ({r['colon']['per10k']}/10k)")
    print(f"  paren          : {r['paren']['count']:4d}  ({r['paren']['per10k']}/10k)")
    print(f"  bullets        : {r['bullets']:4d}")
    print(f"  sentence-len CV: {r['sent_len_cv']}   [human >0.4 typical; <0.3 = too uniform]")
    print(f"  passive (rough): {r['passive_rough']['count']:4d}  ({r['passive_rough']['per10k']}/10k)")
    if r["ai_phrases"]:
        print("  AI phrases     : " + ", ".join(f"{k}×{v}" for k, v in r["ai_phrases"].items()))


if __name__ == "__main__":
    main()
