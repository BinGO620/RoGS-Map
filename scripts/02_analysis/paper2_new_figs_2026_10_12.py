#!/usr/bin/env python
"""paper2_new_figs_2026_10_12.py — 论文2 新增 4 图生成器（2026-10-12）。

生成（全部过 nature-figure 碰撞审计 0 fail + 字号门 ≥5pt）：
  - fig1_arch.pdf          系统架构矢量示意图（替换原生图位图）
  - fig7_4d_rd.pdf         4D codec R-D 曲线（4-12bit）
  - fig8_dyn_cost.pdf      §6 跨序列擦除代价条形图
  - fig9_4d_gen.pdf        4D codec 泛化（4 序列压缩比 + J1 保持率）

数据源：probe_4d_compress_2026-10-12.md / dyn_cost_5seq_2026-10-05.json
运行：python scripts/02_analysis/paper2_new_figs_2026_10_12.py
输出到 papers/paper2/figs/。
"""
import sys
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "papers/paper2/figs"
C_ONLINE, C_OFFLINE, C_MAP = '#0072B2', '#D55E00', '#009E73'


def fig_arch():
    plt.rcParams.update({'font.size': 10})
    fig, ax = plt.subplots(figsize=(6.2, 2.5))
    ax.set_xlim(0, 10.2); ax.set_ylim(0, 3.8); ax.axis('off')

    def box(x, y, w, h, text, color, dashed=False, fs=11):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.06,rounding_size=0.12',
                     fc=color+'18', ec=color, lw=1.3, ls='--' if dashed else '-'))
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=fs, color='#222', zorder=5, fontweight='medium')

    def arrow(x0, y0, x1, y1, color='#333', dashed=False, lw=1.2):
        ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle='-|>',mutation_scale=11,
                     color=color, lw=lw, ls='--' if dashed else '-'))

    ax.text(0.2, 3.42, 'Online SLAM loop (prior stack)', fontsize=11, color=C_ONLINE, fontweight='bold')
    box(0.15,2.35,1.6,0.62,'RGB-D\nframes',C_ONLINE)
    box(2.0,2.35,1.75,0.62,'tracking\n(pose vs map)',C_ONLINE)
    box(4.0,2.35,1.7,0.62,'dynamic\nweighting',C_ONLINE)
    box(5.95,2.35,1.85,0.62,'3DGS map\n(grown online)',C_MAP)
    box(8.05,2.35,1.85,0.62,'rasterised\nrender',C_ONLINE)
    for x0,x1 in [(1.75,2.0),(3.75,4.0),(5.7,5.95),(7.8,8.05)]:
        arrow(x0,2.66,x1,2.66)
    ax.text(0.2, 1.72, 'Offline, map-side (this paper)', fontsize=11, color=C_OFFLINE, fontweight='bold')
    box(2.3,0.5,2.9,0.68,'offline map codec\n(compresses stored map)',C_OFFLINE,dashed=True,fs=10)
    box(5.75,0.5,3.0,0.68,'offline dynamic repair\n(restores erased content)',C_OFFLINE,dashed=True,fs=10)
    arrow(6.3,2.35,4.2,1.18,color=C_OFFLINE,dashed=True,lw=1.1)
    arrow(7.2,2.35,6.9,1.18,color=C_OFFLINE,dashed=True,lw=1.1)
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT/'fig1_arch.pdf'); fig.savefig(OUT/'fig1_arch.png', dpi=300)


def fig_4d_rd():
    # 数据源（全部读盘/报告定稿值，零手抄；口径 = probe_4d_compress_2026-10-12.md 修复后）：
    #   12-bit / 4-bit → evidence_4d12bit/ratio_{12,4}bit.json + <seq>_R1_{12,4}bit_samepose.json（判据机）
    #   8-bit / 10,6,4,6,6 / 6-bit → 报告 v3 定稿表（u8 7.12×/7.95；定稿 8.12×/7.63；6bit 10.07×/3.13）
    ev = REPO / "results/dynport_offline/evidence_4d12bit"
    r12 = json.load(open(ev / "ratio_12bit.json"))["crowd2_R1"]["ratio"]
    j12 = json.load(open(ev / "crowd2_R1_12bit_samepose.json"))["J1_samepose_bad_psnr_delta"]["median"]
    r4 = json.load(open(ev / "ratio_4bit.json"))["crowd2_R1"]["ratio"]
    j4 = json.load(open(ev / "crowd2_R1_4bit_samepose.json"))["J1_samepose_bad_psnr_delta"]["median"]
    pts = [
        (r12, j12, '12-bit'),
        (7.12, 7.95, '8-bit'),
        (8.12, 7.63, '10/6/4/6/6'),
        (10.07, 3.13, '6-bit'),
        (r4, j4, '4-bit'),
    ]
    pts.sort()
    r=[p[0] for p in pts]; j=[p[1] for p in pts]
    plt.rcParams.update({'font.size':9,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9})
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    ax.axvspan(10,17.5,color='#D55E00',alpha=0.07,zorder=0)
    ax.plot(r,j,'-',color='#0072B2',lw=1.8,zorder=3); ax.plot(r,j,'o',color='#0072B2',ms=5,zorder=4)
    ax.axhline(7.95,color='gray',ls='--',lw=0.8,zorder=1)
    ax.plot([8.12],[7.63],'o',ms=9,mfc='none',mec='#D55E00',mew=1.8,zorder=5)
    WB = dict(boxstyle='round,pad=0.15',fc='white',ec='none',alpha=0.9)
    ax.annotate('4-bit',(r4,j4),textcoords='offset points',xytext=(-16,-13),fontsize=8,color='#333',bbox=WB)
    ax.annotate('6-bit',(10.07,3.13),textcoords='offset points',xytext=(7,8),fontsize=8,color='#333',bbox=WB)
    ax.annotate('8-bit',(7.12,7.95),textcoords='offset points',xytext=(-8,-14),fontsize=8,color='#333',bbox=WB)
    ax.annotate('12-bit',(r12,j12),textcoords='offset points',xytext=(-10,9),fontsize=8,color='#333',bbox=WB)
    ax.annotate('working\npoint',xy=(8.12,7.63),xytext=(13.5,7.4),textcoords='data',fontsize=8,color='#8B3A00',
                ha='center',va='center',arrowprops=dict(arrowstyle='->',color='#8B3A00',lw=0.9),bbox=WB,zorder=6)
    ax.text(14.5,5.8,'criterion\nbroken',fontsize=8,color='#8B3A00',ha='center',va='center',zorder=4,bbox=WB)
    ax.text(4.0,8.55,'uncompressed',fontsize=7.5,color='gray',va='bottom',bbox=WB)
    ax.set_xlabel('compression ratio (×)'); ax.set_ylabel('J1: dynamic-region PSNR gain (dB)')
    ax.set_xlim(2.5,18); ax.set_ylim(0,9); ax.set_xticks([4,6,8,10,12,14,16,18])
    for s in ('top','right'): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT/'fig7_4d_rd.pdf'); fig.savefig(OUT/'fig7_4d_rd.png', dpi=300)


def fig_dyn_cost():
    d = json.load(open(REPO/'results/paper2_fulltable/evidence/dyn_cost_5seq_2026-10-05.json'))
    rows = [(r['seq'], r['bad_psnr_gain_db']) for r in d['rows'] if r['arm']=='baseline']
    rows.sort(key=lambda x: x[1])
    seqs=[r[0] for r in rows]; gains=[r[1] for r in rows]
    colors=['#D55E00' if 'crowd' in s else '#0072B2' if s=='person_tracking' else '#009E73' for s in seqs]
    plt.rcParams.update({'font.size':9,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9})
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    y=np.arange(len(seqs)); ax.barh(y,gains,color=colors,height=0.6)
    ax.set_yticks(y); ax.set_yticklabels(seqs,fontsize=8.5)
    ax.set_xlabel('dynamic-region PSNR gain (dB)'); ax.set_xlim(0,25)
    for i,g in enumerate(gains): ax.text(g+0.5,i,f'{g:.1f}',va='center',fontsize=8.5)
    for s in ('top','right'): ax.spines[s].set_visible(False)
    fig.tight_layout(pad=0.4); fig.savefig(OUT/'fig8_dyn_cost.pdf'); fig.savefig(OUT/'fig8_dyn_cost.png', dpi=300)


def fig_4d_gen():
    seqs=['crowd2','crowd','balloon2','person_tracking']; ratios=[8.12,7.87,8.08,9.31]; keep=[96,87,84,91]
    plt.rcParams.update({'font.size':10,'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10})
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(5.2,2.2)); y=np.arange(4)[::-1]
    ax1.barh(y,ratios,color='#0072B2',height=0.6); ax1.set_yticks(y); ax1.set_yticklabels(seqs,fontsize=10)
    ax1.set_xlabel('compression ratio (×)'); ax1.set_xlim(0,11.5)
    for i,r in zip(y,ratios): ax1.text(r+0.2,i,f'{r:.1f}',va='center',fontsize=10)
    for s in ('top','right'): ax1.spines[s].set_visible(False)
    ax2.barh(y,keep,color='#009E73',height=0.6); ax2.set_yticks(y); ax2.set_yticklabels(seqs,fontsize=10)
    ax2.set_xlabel('J1 kept (%)'); ax2.set_xlim(0,115)
    for i,k in zip(y,keep): ax2.text(k+2,i,f'{k}',va='center',fontsize=10)
    ax2.axvline(80,color='gray',ls='--',lw=0.8)
    for s in ('top','right'): ax2.spines[s].set_visible(False)
    fig.tight_layout(pad=0.4); fig.savefig(OUT/'fig9_4d_gen.pdf'); fig.savefig(OUT/'fig9_4d_gen.png', dpi=300)


if __name__ == '__main__':
    fig_arch(); fig_4d_rd(); fig_dyn_cost(); fig_4d_gen()
    print(f'wrote 4 figures to {OUT}')
