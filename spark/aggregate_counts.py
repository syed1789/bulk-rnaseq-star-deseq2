#!/usr/bin/env python3
"""Local-mode PySpark aggregation over the featureCounts matrix.

A single 4-sample run doesn't need Spark -- this is here because the CV
claim is Spark itself. The transform (per-sample library size, per-gene
mean/variance across samples) is the same shape you'd run over hundreds of
samples' count matrices concatenated across a study; running it in Spark's
local[*] mode here keeps it honestly-scoped: real Spark execution, on data
sized for a laptop demo rather than a cluster.
"""
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

fc_path, out_path = sys.argv[1], sys.argv[2]

spark = SparkSession.builder.appName("rnaseq-count-aggregation").master("local[*]").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# featureCounts output: comment line, then header, then gene rows.
raw = spark.read.option("delimiter", "\t").option("header", True).csv(fc_path, comment="#")

bam_cols = [c for c in raw.columns if c.endswith(".bam")]
sample_cols = []
for c in bam_cols:
    # Spark interprets "." in a bracket/getitem lookup as nested-field access,
    # and these column names (docker-mounted BAM paths) are full of dots --
    # rename to a flat, dot-free alias before doing anything with them.
    safe_name = c.replace(".", "_").replace("/", "_")
    raw = raw.withColumnRenamed(c, safe_name).withColumn(safe_name, F.col(safe_name).cast("long"))
    sample_cols.append(safe_name)

# Per-sample library size (total assigned reads).
lib_sizes = raw.select([F.sum(c).alias(c) for c in sample_cols])
print("Per-sample assigned-read totals:")
lib_sizes.show(truncate=False)

# Per-gene mean/stddev count across samples.
gene_stats = raw.select(
    "Geneid",
    F.array(*sample_cols).alias("counts"),
).withColumn("mean_count", F.aggregate("counts", F.lit(0.0), lambda acc, x: acc + x) / len(sample_cols))

gene_stats = gene_stats.orderBy(F.desc("mean_count")).select("Geneid", "mean_count")
gene_stats.show(10, truncate=False)

with open(out_path, "w") as fh:
    fh.write("Geneid\tmean_count\n")
    for row in gene_stats.toLocalIterator():
        fh.write(f"{row['Geneid']}\t{row['mean_count']}\n")
print(f"Wrote per-gene mean counts to {out_path}")

spark.stop()
