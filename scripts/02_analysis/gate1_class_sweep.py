#!/usr/bin/env python3
"""gate1_class_sweep.py — 关卡①「已撤回陈述仍作活跃结论」机械类扫（可复跑、可变红）

用法（仓库根目录）:
    /data/conda_envs/monogs-ours/bin/python scripts/02_analysis/gate1_class_sweep.py [--quiet]
    /data/conda_envs/monogs-ours/bin/python -m pytest tests/lifecycle_paper2 -q   # 负/正对照

背景：verdict_L1 的关卡① 前五轮 Reject 中，"撤回措辞仍作活跃结论"这一**类别**反复出现。
第 6 轮审查指出本脚本的两个缺陷（已修）：
  (a) MARKERS 含裸词（"四轮"/"候选 0"）⇒ 旧轮次/旧预算行被判 MARKED，**自掩蔽**；
  (b) 账目类关键词硬编码旧字符串 ⇒ 对**轮次数字本身失明**。
因此现在：MARKERS 只收整句形状词；轮次用**独立的一致性检查**（ROUND_CANON）；
并以 `tests/lifecycle_paper2/test_gate1_class_sweep.py` 的**负对照**证明本门禁能变红。

规则：
- 关键词集按类分组（口径 / 账目 / 预算与实装），新增类别写进 GROUPS 即可；
- 命中行若本行或紧邻下一行无撤回标记即 UNMARKED；轮次非规范写法计 ROUND?；两者皆以非零退出码门禁；
- `prereg_L1.md` 属冻结原文，不进文件列表。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 归档镜像（2026-10-11）：已关闭族的四件套整体移入 `archive/closed_families/<族>/`，
# 逻辑路径仍是 `results/<族>/…`。受检文件若活区不存在即按镜像解析；解析到归档**仍算受检**
# （内容一字未改，门禁语义不变），但**缺件不再是静默 [skip]** —— 静默跳过会让本门禁
# 恒绿（2026-10-11 发现：swba_lifecycle/mope_layer 两族归档后 VOIDREF/ALPHA-CONFLICT
# 两类检查空转且不报错）。
ARCHIVE_MIRROR = "archive/closed_families"


def resolve(rel: str) -> Path | None:
    """逻辑路径 → 实际文件：先活区，再归档镜像（results/<族>/<rest> → archive/closed_families/<族>/results/<rest>）。"""
    p = REPO / rel
    if p.is_file():
        return p
    m = re.match(r"^results/([^/]+)/(.+)$", rel)
    if m:
        cand = REPO / ARCHIVE_MIRROR / m.group(1) / "results" / m.group(2)
        if cand.is_file():
            return cand
    return None


FILES = [
    "results/lifecycle_paper2/evidence/verdict_L1.md",
    "results/lifecycle_paper2/evidence/crowd_degradation_improvement_2026-09-20.md",
    "results/lifecycle_paper2/evidence/crowd_judgeability_2026-09-20.md",
    # L3 正式批（2026-09-20 加入；按类扫，别按点扫——P30 教训：Reject 后只改被点名行
    # ⇒ 同类残留连绵五轮。新增的预注册/修正案/裁决文本一律纳入本门禁）
    "results/lifecycle_paper2/evidence/prereg_L3.md",
    "results/lifecycle_paper2/evidence/prereg_L3_amendment_1_frameset.md",
    "results/lifecycle_paper2/evidence/verdict_L3.md",
    "results/lifecycle_paper2/README.md",
    "resources/lit_dyn_mapping/occupancy_recheck_2026-09-20.md",
    "DECISIONS.md",
    "NOTES.md",
    # 2026-10-11 拆分：事件流水 → LOG.md、坑库 → PITFALLS.md（负结果包装类更正块在坑库）
    "LOG.md",
    "PITFALLS.md",
    # 写作轨（2026-09-23 加入；违纪起因 = 把负结果包装成主张/headline，
    # 见 NOTES 踩坑区"负结果包装"条目与 DECISIONS D1-010）
    "results/lifecycle_paper2/evidence/paper2_skeleton.md",
    "results/lifecycle_paper2/evidence/verdict_L1c_occupancy.md",
    # swba_lifecycle 族（2026-10-01 立项；VOIDED 表中的 §2-B/§2-C 引用一致性由本门禁守护）
    "results/swba_lifecycle/evidence/prereg_swba_lifecycle.md",
    # mope_layer 族（2026-10-02 立项；ALPHA-CONFLICT 检查由本门禁守护）
    "results/mope_layer/evidence/prereg_mope_layer.md",
]

GROUPS: dict[str, list[str]] = {
    # 数据/口径类（第 1–4 轮的主要残留族）
    "口径": ["8 帧口径", "只渲染 8 帧", "80×", "0.647", "25.6m", "58–65", "194 个", "机制退化",
             "离线不可评测", "≥−0.22", "留下退化", "拥挤场景特有", "恢复三件套"],
    # 轮次账目类（关键词 = **当前**已过时的轮次写法，随 ROUND_CANON 进位而更新）
    "账目": ["待第 5 轮", "已送四轮", "已送三轮", "待四轮", "待第 4 轮", "② 轮未送", "二轮残留"],
    # 预算与实装状态类
    "预算": ["2–4 run", "~3–4h", "2h GPU", "零实装"],
    # 负结果身份类（DISCIPLINE.md「论文叙事纪律」）：把负结果包装成主张/贡献/headline/自造名。
    # 注意：GROUPS 是**字面子串**匹配（非正则）——只放确凿的包装性措辞。
    "负结果身份": ["可讲的负结果", "负结果的故事", "否定链", "边界叙事素材",
                   "负结果作为贡献", "负结果的贡献", "负结果可作贡献"],
}

# 轮次一致性：正式文本只允许出现下列规范写法（每次复核进位时同步更新）。
ROUND_CANON = ("已送 7 轮",)   # 单一事实源：轮次只在 DECISIONS.md 出现
ROUND_ANY = re.compile(r"(已送\s*[一二三四五六七八九十\d]+\s*轮|待第\s*\d+\s*轮|待\s*[一二三四五六七八九十]+\s*轮)")

# 标记集**只收整句形状**的词（裸词会让旧轮次/旧预算行自掩蔽）
MARKERS = re.compile(
    "撤回|作废|§8|已改|改判|~~|不可判|更正|推翻|降级|本条为准|不再活跃|"
    "近零实装|上限 8 run|诊断级|止损|不适用|本形态默认"
)

# ── 内部交叉引用一致性（2026-10-01 加入；来源 = swba_lifecycle G4 复核，P30 类）─────────
# 类：某节/项被判**作废**后，文内**其余引用点**未同步标注 ⇒ 读者会把作废物当活跃件
# （本类在 swba_lifecycle 首轮 G4 被抓到：§2-B/§2-C 已在 §2/§9 标废，但 §1.2/§3/§5/§8 的
#  引用点仍是"点改"而非"类扫" ⇒ 与本门禁第 8 行自述的 P30 教训同型）。
# 载体 = 本表（文件 → 已作废标签）；该文件内任一"引用点"须带 VOID_MARKERS，否则计 VOIDREF。
VOIDED: dict[str, list[str]] = {
    "results/swba_lifecycle/evidence/prereg_swba_lifecycle.md": ["§2-B", "§2-C"],
}
VOID_MARKERS = re.compile("作废|~~|不成立|推翻|已改|不可判|更正|降级|待 v2|呈报")


# ── per-primitive α 动作 ⇔ 撞墙 A（2026-10-02 加入；来源 = mope_layer G1 致命项，P30 类）─────
# 类：某 prereg 声称"绕开 α 通道共线墙（D2-017）"，却在机制里引入 **per-primitive α 操作**
#   （如 `α_i ← ...` / 改 static_prob / 改 opacity per-primitive）⇒ 自相矛盾，必撞墙 A。
# 载体 = 本表（文件 → 行内含"不撞墙/绕开 α/不经 α_eff"的声明），若同文件另有 per-primitive α
#   动作行，则计 ALPHA-CONFLICT（rc=1）。
ALPHA_AVOID = re.compile("不撞墙 A|绕开.*α|未经.*α_eff|不经 α_eff|不走 α")
ALPHA_OP = re.compile("α_i|alpha_i|opacity\\s*←|opacity_i|static_prob\\s*←|per-primitive.*α|高斯级.*α|逐基元.*α")
# 文档化"已删除该动作"的行（整改/变更记录/删除说明）不算冲突
ALPHA_VOID = re.compile("删|作废|不取|已删|整改|不含|不再|~~")
# 本检查**只对 prereg 规格件**生效（大文件如 DECISIONS.md 含大量叙述性 "="，启发式会假阳）
ALPHA_SCOPE = re.compile(r"results/[^/]+/evidence/prereg_.*\.md$")


def scan_alpha_conflict(rel: str, lines: list[str]) -> int:
    """检「声称绕开 α 墙却含 per-primitive α 动作」；返回冲突数（>0 ⇒ 门禁变红）。

    仅扫 prereg 规格件（ALPHA_SCOPE）；忽略带删除/整改标记的行、引用块（`>`）、
    "墙 A 定义"类命题行，以及不含动作符（`←`/`=`/"改变"/"操作"）的纯陈述行。
    **已知局限**：逐行启发式；定位为 G1 **提醒项**，非唯一裁决。"""
    if not ALPHA_SCOPE.search(rel):
        return 0
    claimed = any(ALPHA_AVOID.search(l) for l in lines)
    if not claimed:
        return 0
    bad = 0
    for i, line in enumerate(lines):
        if not ALPHA_OP.search(line):
            continue
        if ALPHA_VOID.search(line) or VOID_MARKERS.search(line):
            continue
        if line.lstrip().startswith(">"):
            continue
        if "必经" in line or "与信号源无关" in line:
            continue
        if "←" not in line and "=" not in line and "改变" not in line and "操作" not in line:
            continue
        bad += 1
        print(f"ALPHA-CONFLICT {rel}:{i + 1} 声称绕开 α 墙但含 per-primitive α 动作 ⇒ 撞墙 A（D2-017）")
    return bad


def scan_void_refs(rel: str, lines: list[str], quiet: bool = False) -> int:
    """扫「已作废标签的未标注引用点」；返回 VOIDREF 计数（>0 ⇒ 门禁变红）。"""
    labels = VOIDED.get(rel)
    if not labels:
        return 0
    bad = 0
    for i, line in enumerate(lines):
        for lab in labels:
            if lab not in line:
                continue
            if VOID_MARKERS.search(line):
                continue                      # 标注了（含"作废/不成立/待 v2"等）⇒ 合规
            bad += 1
            print(f"VOIDREF  {rel}:{i + 1} 引用了已作废标签 {lab} 但本行无作废标记 "
                  f"⇒ 同义类扫（P30）")
    return bad

# 显式放行（每条写明理由；放行项单独打印为 ALLOWED，不计入 UNMARKED）
ALLOW = [
    (re.compile(r"R7 的.*2–4\s*run|L1 最小效果验证（2–4 run"),
     "引用 R7 纪律原文（宪法条款），非本仓预算主张"),
    (re.compile(r"零实装（只切|reset-only"),
     "候选 2 的实装成本描述（与候选 0 无关）"),
    (re.compile(r"非\"零实装\"|（非“零实装”）"),
     "候选 0 的澄清说明自身"),
    (re.compile(r"实际恰好相反|离线不可评测\"之处|一律以本条为准"),
     "踩坑条目/更正块在引用旧措辞（说明其已被推翻）"),
    (re.compile(r"L1 沉没 ≈2h GPU"),
     "D2-014 账本行可逆性列（呈报选项乙的沉没成本事实，非活跃批预算主张）"),
    (re.compile(r"修正案.*2–4 run|L1 规模 2–4 run"),
     "D2-020 呈报选项甲的修正案批规模（R7 L1 阶梯 + R2 条款；授权源 = 同行账本，非新增无主预算）"),
    # 负结果身份类：纪律原文引用与更正块（都必然包含被禁措辞）显式放行
    (re.compile(r"负结果不得作论文叙事主角|负结果\*\*只以|不进贡献栏、不起包装性命名"),
     "引用 DISCIPLINE.md「论文叙事纪律」 纪律原文（宪法条款），非本仓主张"),
    (re.compile(r"违纪更正|违纪登记|已撤回该表述|改此|原写|私起包装性名称"),
     "更正块/踩坑条目在引用被撤回的旧措辞（说明其已作废）"),
]


def scan_lines(rel: str, lines: list[str], quiet: bool = False) -> tuple[int, int, int, int]:
    """扫单个文件的文本行；返回 (命中, UNMARKED, ALLOWED, 轮次非规范)。"""
    total = unmarked = allowed = rounds_bad = 0
    for i, line in enumerate(lines):
        # ① 轮次一致性（独立于关键词类）
        for m in ROUND_ANY.finditer(line):
            txt = re.sub(r"\s+", " ", m.group(0))
            # 单一事实源：轮次数字只允许出现在账本（DECISIONS.md）；NOTES/LOG/PITFALLS
            # 为历史流水（记录用）放行（2026-10-11：NOTES 拆分后三件同权）
            if rel in ("NOTES.md", "LOG.md", "PITFALLS.md"):
                pass                      # 历史流水，轮次记录用，跳过
            elif rel != "DECISIONS.md":
                rounds_bad += 1
                print(f"ROUND-dup {rel}:{i + 1} 轮次数字重复出现「{txt}」"
                      f"⇒ 改为指向 DECISIONS.md D1-003（单一事实源）")
            elif not any(c.replace(" ", "") in txt.replace(" ", "") for c in ROUND_CANON):
                rounds_bad += 1
                print(f"ROUND?   {rel}:{i + 1} 账本内轮次写法非规范「{txt}」"
                      f"（规范: {' / '.join(ROUND_CANON)}）")
        # ② 关键词类 × 撤回标记
        for group, words in GROUPS.items():
            for w in words:
                if w not in line:
                    continue
                total += 1
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if MARKERS.search(line) or MARKERS.search(nxt):
                    if not quiet:
                        print(f"MARKED   {rel}:{i + 1} [{group}/{w}]")
                    continue
                hit = next(((r, why) for r, why in ALLOW if r.search(line)), None)
                if hit is not None:
                    allowed += 1
                    print(f"ALLOWED  {rel}:{i + 1} [{group}/{w}] 理由: {hit[1]}")
                    continue
                unmarked += 1
                print(f"UNMARKED {rel}:{i + 1} [{group}/{w}] {line.strip()[:100]}")
    return total, unmarked, allowed, rounds_bad


def sweep(quiet: bool = False) -> int:
    total = unmarked = allowed = rounds_bad = voidref = alphaconf = 0
    missing = 0
    for rel in FILES:
        path = resolve(rel)
        if path is None:
            # 缺件**必须变红**：静默 [skip] 会让本门禁对整族检查空转（2026-10-11 修）。
            missing += 1
            print(f"[MISSING] 受检文件不存在（活区与归档镜像皆无）: {rel}")
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        t, u, a, r = scan_lines(rel, lines, quiet)
        total += t
        unmarked += u
        allowed += a
        rounds_bad += r
        voidref += scan_void_refs(rel, lines, quiet)
        alphaconf += scan_alpha_conflict(rel, lines)
    groups = "/".join(GROUPS)
    print(f"\n机械类扫：{len(FILES)} 文件 × 类别[{groups}]，命中 {total}，"
          f"ALLOWED {allowed}（放行理由见上），UNMARKED = {unmarked}，"
          f"轮次非规范 = {rounds_bad}（规范: {' / '.join(ROUND_CANON)}），"
          f"失效引用 = {voidref}（VOIDED 表 {len(VOIDED)} 文件），α 墙冲突 = {alphaconf}，"
          f"缺件 = {missing}")
    return 1 if (unmarked or rounds_bad or voidref or alphaconf or missing) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="只打印 UNMARKED/ALLOWED/ROUND? 与汇总")
    sys.exit(sweep(ap.parse_args().quiet))
