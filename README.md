# Bulk RNA-seq: STAR → featureCounts → DESeq2, orchestrated with Snakemake

**Author:** Syed Nurul Hasan, Ph.D.
**Contact:** nayanchoton1789@gmail.com | [ORCID: 0000-0002-4564-872X](https://orcid.org/0000-0002-4564-872X)

---

## Why this project

My existing public pipelines (`nf-variant-pipeline`, `bioinformatics-portfolio`) use Nextflow, Seurat, and Scanpy — real tools I use daily — but several roles I've applied to also named STAR, DESeq2, Snakemake, SLURM, and SQL specifically, and none of those had a public repo behind them. This one does: a real STAR alignment, real featureCounts quantification, real DESeq2 differential expression, all wired together as an actual Snakemake DAG (not a shell script pretending to be one), plus a SLURM cluster profile, an S3/AWS-Batch profile, a SQLite results store with example queries, and a local-mode PySpark aggregation step.

## Pipeline

```
FASTQ (paired-end, 4 samples, GSE110004 subset)
        │
        ▼
1. star_index / star_align  (Docker: biocontainers/star)
   └── genome + splice-aware alignment → sorted BAM per sample
        │
        ▼
2. feature_counts  (Docker: biocontainers/subread)
   └── gene-level count matrix (paired-end, --countReadPairs)
        │
        ▼
3. deseq2  (R, DESeq2 — run natively, no container needed)
   └── WT vs. RAP1_IAA_30M differential expression
        │
        ├──▶ 4a. load_sqlite   → sql/rnaseq.db + example SQL queries
        └──▶ 4b. spark_aggregate → local-mode PySpark per-sample/per-gene summary
```

All of the above is one Snakemake DAG (`workflow/Snakefile`, `snakemake --cores 4`).
`airflow/dag_bulk_rnaseq.py` shows the same pipeline re-expressed as an Airflow
DAG (one task per Snakemake target) for shops where Airflow is the standing
scheduler — actually executed and verified end-to-end via `airflow dags test`
(Airflow 3.3.0, local SQLite metadata DB), not just written and left untested;
`workflow/profiles/slurm/` and `workflow/profiles/aws/` are real, usable
Snakemake executor profiles for cluster/cloud execution.

## Dataset

Paired-end FASTQ subsets + a matching genome/GTF subset from
[nf-core/test-datasets](https://github.com/nf-core/test-datasets) (`rnaseq`
branch), which in turn derive from **GSE110004** — Challal et al., "Repression
of Divergent Noncoding Transcription by a Sequence-Specific Transcription
Factor" (*Molecular Cell*, 2018) — a yeast Rap1 anchor-away RNA-seq study.

**Why yeast, and why subsetted:** the CV gap here is the STAR/DESeq2/Snakemake
*mechanics*, not a new biological finding — the genome/GTF/reads are
deliberately shrunk (nf-core's own CI test fixtures) so the whole DAG runs in
under two minutes on a laptop, with zero risk of an hours-long human-genome
STAR index build eating the session. The same rules run unmodified against a
full genome and full-depth FASTQs; only the `--genomeSAindexNbases` value
needs to go back to STAR's default for a real-sized genome.

**Design caveat, stated plainly:** this run compares WT (n=3: SRR6357070,
SRR6357071, SRR6357072) against RAP1_IAA_30M (n=1: SRR6357076) because that's
what this particular test-data subset contains — DESeq2 runs and produces a
real result, but a single replicate in the treatment arm is not a properly
powered comparison. Scaling to the full GSE110004 series (more SRR runs, more
replicates per condition) is a one-line change to `SAMPLES` in the Snakefile.

## Results (this run)

- STAR: 82–85% uniquely-mapped reads across all 4 samples.
- featureCounts: 76–78% of alignments successfully assigned to genes (`--countReadPairs`).
- DESeq2: 82 genes tested after low-count filtering; **4 genes at padj < 0.05**
  (YAR010C, YAR009C, YAL038W, YAL003W) — full table in
  [`results/deseq2_results.tsv`](results/deseq2_results.tsv).
- SQL: [`scripts/load_sqlite.py`](scripts/load_sqlite.py) loads the DESeq2
  table into `sql/rnaseq.db` and runs example queries (significant genes by
  effect size, counts by significance bucket) — output reproduced in the
  Snakemake log.
- Spark: [`spark/aggregate_counts.py`](spark/aggregate_counts.py) runs a
  local-mode (`local[*]`) PySpark job computing per-sample library size and
  per-gene mean count across samples — see
  [`spark/sample_summary.tsv`](spark/sample_summary.tsv). Honestly scoped: a
  4-sample matrix doesn't need Spark, but the transform is the same shape
  you'd run over hundreds of samples' concatenated count matrices, and this
  is real Spark execution rather than a pandas script relabeled.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install snakemake pyspark

# Full DAG: STAR -> featureCounts -> DESeq2 -> {SQLite, Spark}
snakemake -s workflow/Snakefile --cores 4 -p

# SLURM cluster execution (real profile, not run here -- no cluster in this environment)
snakemake -s workflow/Snakefile --workflow-profile workflow/profiles/slurm

# S3/AWS Batch execution (real profile, not run here -- no AWS credentials in this environment)
snakemake -s workflow/Snakefile --workflow-profile workflow/profiles/aws
```

## Key Features

- Real STAR alignment and featureCounts quantification, containerized (no local install required)
- Real DESeq2 differential expression
- An actual Snakemake DAG — rule dependencies, not a linear shell script
- SLURM and AWS Batch executor profiles (config-as-code, matching the profile
  pattern already used in my `nf-variant-pipeline` repo)
- SQLite results store + example SQL
- Local-mode PySpark aggregation
- Airflow DAG expressing the same pipeline for scheduler-centric shops —
  actually run via `airflow dags test`, all 6 tasks succeeded

## References

1. Challal D, Barucco M, Kubik S, et al. Repression of Divergent Noncoding
   Transcription by a Sequence-Specific Transcription Factor. *Molecular
   Cell*. 2018;72(6):955-969.e7. (GSE110004)
2. Dobin A, Davis CA, Schlesinger F, et al. STAR: ultrafast universal RNA-seq
   aligner. *Bioinformatics*. 2013;29(1):15-21.
3. Liao Y, Smyth GK, Shi W. featureCounts: an efficient general-purpose
   program for assigning sequence reads to genomic features.
   *Bioinformatics*. 2014;30(7):923-930.
4. Love MI, Huber W, Anders S. Moderated estimation of fold change and
   dispersion for RNA-seq data with DESeq2. *Genome Biology*. 2014;15:550.
5. Mölder F, Jablonski KP, Letcher B, et al. Sustainable data analysis with
   Snakemake. *F1000Research*. 2021;10:33.

## License

MIT — see [LICENSE](LICENSE).
