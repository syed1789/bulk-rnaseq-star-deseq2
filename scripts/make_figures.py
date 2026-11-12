#!/usr/bin/env python3
"""Figures from the DESeq2 / featureCounts / STAR outputs -> results/figures/."""
import re
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path("results"); F = R / "figures"; F.mkdir(exist_ok=True)
de = pd.read_csv(R / "deseq2_results.tsv", sep="\t").dropna(subset=["padj"])
sig = de.padj < 0.05
up, dn = sig & (de.log2FoldChange > 0), sig & (de.log2FoldChange < 0)

fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(de.log2FoldChange[~sig], -np.log10(de.pvalue[~sig]), s=4, c="#999", alpha=.5)
ax.scatter(de.log2FoldChange[up], -np.log10(de.pvalue[up]), s=8, c="#c44e52", label=f"up ({up.sum()})")
ax.scatter(de.log2FoldChange[dn], -np.log10(de.pvalue[dn]), s=8, c="#4c72b0", label=f"down ({dn.sum()})")
for _, r in de[sig].nsmallest(10, "padj").iterrows():
    ax.annotate(r.gene, (r.log2FoldChange, -np.log10(r.pvalue)), fontsize=6)
ax.set_xlabel("log2 fold change (RAP1_IAA_30M vs WT)"); ax.set_ylabel("-log10 p-value")
ax.set_title("Volcano plot (padj<0.05)"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(F / "volcano.png", dpi=130); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(np.log10(de.baseMean + 1), de.log2FoldChange, s=4, c=np.where(sig, "#c44e52", "#999"), alpha=.6)
ax.axhline(0, c="k", lw=.5); ax.set_xlabel("log10 mean normalized count"); ax.set_ylabel("log2 fold change")
ax.set_title("MA plot"); fig.tight_layout(); fig.savefig(F / "ma_plot.png", dpi=130); plt.close(fig)

fc = pd.read_csv(R / "featurecounts.txt", sep="\t", comment="#", index_col=0).iloc[:, 5:]
fc.columns = [re.search(r"(SRR\d+)", c).group(1) for c in fc.columns]
fc = fc[fc.sum(axis=1) > 10]
logcpm = np.log2(fc / fc.sum() * 1e6 + 1)
cond = {"SRR6357070": "WT", "SRR6357071": "WT", "SRR6357072": "WT", "SRR6357076": "RAP1_IAA_30M"}
x = logcpm.T - logcpm.T.mean()
u, s, _ = np.linalg.svd(x.values, full_matrices=False)
pc = u * s; var = s**2 / (s**2).sum() * 100
fig, ax = plt.subplots(figsize=(5, 4.5))
for i, n in enumerate(x.index):
    ax.scatter(pc[i, 0], pc[i, 1], s=70, c="#c44e52" if cond[n] != "WT" else "#4c72b0")
    ax.annotate(f"{n}\n{cond[n]}", (pc[i, 0], pc[i, 1]), fontsize=7, xytext=(4, 4), textcoords="offset points")
ax.set_xlabel(f"PC1 ({var[0]:.0f}%)"); ax.set_ylabel(f"PC2 ({var[1]:.0f}%)"); ax.set_title("PCA of log2 CPM")
fig.tight_layout(); fig.savefig(F / "pca.png", dpi=130); plt.close(fig)

rows = []
for p in sorted((R / "star").glob("*_Log.final.out")):
    t = p.read_text()
    g = lambda k: float(re.search(k + r"\s*\|\s*([\d.]+)%?", t).group(1))
    rows.append((p.name.split("_")[0], g("Uniquely mapped reads %"), g("% of reads mapped to multiple loci"),
                 g("% of reads unmapped: too short")))
st = pd.DataFrame(rows, columns=["sample", "unique", "multi", "unmapped_short"])
fig, ax = plt.subplots(figsize=(6, 3.5))
b = np.zeros(len(st))
for col, c in [("unique", "#4c72b0"), ("multi", "#dd8452"), ("unmapped_short", "#999")]:
    ax.bar(st["sample"], st[col], bottom=b, color=c, label=col); b += st[col].values
ax.set_ylabel("% of input reads"); ax.legend(frameon=False, fontsize=7); ax.set_title("STAR alignment summary")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
fig.tight_layout(); fig.savefig(F / "star_mapping.png", dpi=130); plt.close(fig)
print(f"{len(de)} genes tested; {up.sum()} up, {dn.sum()} down")
