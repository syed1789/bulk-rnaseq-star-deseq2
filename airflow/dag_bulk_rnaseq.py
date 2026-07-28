"""Airflow DAG orchestrating the Snakemake bulk RNA-seq pipeline.

This wraps `snakemake -s workflow/Snakefile` as a single BashOperator task
per logical stage, so the DAG's task graph mirrors the Snakemake rule graph
(star_align -> feature_counts -> deseq2 -> {load_sqlite, spark_aggregate}).
In practice you'd either let Snakemake manage the DAG internally (simplest,
what this repo's CI does) or split it out like this when Airflow is already
the shop's scheduler and you want cross-pipeline dependencies, retries, and
alerting Snakemake alone doesn't give you.
"""
from __future__ import annotations

import os

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

# Mounted/checked-out path of this repo on the Airflow worker. Defaults to
# "/work" (a typical container mount point); override via env var for a
# bare-metal/venv worker such as the one this DAG was tested against.
REPO_DIR = os.environ.get("BULK_RNASEQ_REPO_DIR", "/work")


@dag(
    dag_id="bulk_rnaseq_star_deseq2",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["rnaseq", "star", "deseq2", "snakemake"],
)
def bulk_rnaseq_star_deseq2():
    star_align = BashOperator(
        task_id="star_align_all_samples",
        bash_command=(
            f"cd {REPO_DIR} && source .venv/bin/activate && "
            "snakemake -s workflow/Snakefile --cores 4 "
            "results/star/SRR6357070_Aligned.sortedByCoord.out.bam "
            "results/star/SRR6357071_Aligned.sortedByCoord.out.bam "
            "results/star/SRR6357072_Aligned.sortedByCoord.out.bam "
            "results/star/SRR6357076_Aligned.sortedByCoord.out.bam"
        ),
    )

    feature_counts = BashOperator(
        task_id="feature_counts",
        bash_command=(
            f"cd {REPO_DIR} && source .venv/bin/activate && "
            "snakemake -s workflow/Snakefile --cores 4 results/featurecounts.txt"
        ),
    )

    deseq2 = BashOperator(
        task_id="deseq2",
        bash_command=(
            f"cd {REPO_DIR} && source .venv/bin/activate && "
            "snakemake -s workflow/Snakefile --cores 1 results/deseq2_results.tsv"
        ),
    )

    @task
    def summarize_hits() -> dict:
        """Downstream task showing how you'd branch on pipeline results --
        e.g. to decide whether to page someone or open a ticket."""
        import csv

        path = f"{REPO_DIR}/results/deseq2_results.tsv"
        n_sig = 0
        with open(path) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                try:
                    if float(row["padj"]) < 0.1:
                        n_sig += 1
                except (ValueError, TypeError):
                    continue
        return {"significant_genes": n_sig}

    load_sqlite = BashOperator(
        task_id="load_sqlite",
        bash_command=(
            f"cd {REPO_DIR} && source .venv/bin/activate && "
            "snakemake -s workflow/Snakefile --cores 1 sql/rnaseq.db"
        ),
    )

    spark_aggregate = BashOperator(
        task_id="spark_aggregate",
        bash_command=(
            f"cd {REPO_DIR} && source .venv/bin/activate && "
            "snakemake -s workflow/Snakefile --cores 1 spark/sample_summary.tsv"
        ),
    )

    star_align >> feature_counts >> deseq2 >> summarize_hits()
    deseq2 >> [load_sqlite, spark_aggregate]


bulk_rnaseq_star_deseq2()
