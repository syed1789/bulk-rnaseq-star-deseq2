#!/usr/bin/env python3
"""Load the DESeq2 results table into SQLite and run a couple of example
queries -- a stand-in for the kind of ad hoc SQL analysts run against a
results warehouse once a pipeline's output lands somewhere queryable."""
import sqlite3
import sys
import csv

deseq2_tsv, out_db = sys.argv[1], sys.argv[2]

conn = sqlite3.connect(out_db)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS deseq2_results")
cur.execute(
    """
    CREATE TABLE deseq2_results (
        gene TEXT PRIMARY KEY,
        baseMean REAL,
        log2FoldChange REAL,
        lfcSE REAL,
        stat REAL,
        pvalue REAL,
        padj REAL
    )
    """
)

with open(deseq2_tsv) as f:
    reader = csv.DictReader(f, delimiter="\t")
    rows = []
    for r in reader:
        def num(x):
            try:
                return float(x)
            except (ValueError, TypeError):
                return None
        rows.append((
            r["gene"], num(r["baseMean"]), num(r["log2FoldChange"]),
            num(r["lfcSE"]), num(r["stat"]), num(r["pvalue"]), num(r["padj"]),
        ))

cur.executemany(
    "INSERT INTO deseq2_results VALUES (?, ?, ?, ?, ?, ?, ?)", rows
)
conn.commit()

print(f"Loaded {len(rows)} genes into {out_db}")

print("\n-- Significant genes (padj < 0.1), by effect size --")
for row in cur.execute(
    """
    SELECT gene, baseMean, log2FoldChange, padj
    FROM deseq2_results
    WHERE padj < 0.1
    ORDER BY ABS(log2FoldChange) DESC
    """
):
    print(row)

print("\n-- Count of tested genes by significance bucket --")
for row in cur.execute(
    """
    SELECT
        CASE
            WHEN padj < 0.05 THEN 'padj < 0.05'
            WHEN padj < 0.1 THEN '0.05 <= padj < 0.1'
            ELSE 'padj >= 0.1 or NA'
        END AS bucket,
        COUNT(*) AS n_genes
    FROM deseq2_results
    GROUP BY bucket
    """
):
    print(row)

conn.close()
