#!/usr/bin/env Rscript
# Differential expression on the STAR -> featureCounts gene-count matrix.
# Design: WT (n=3: SRR6357070, SRR6357071, SRR6357072) vs
#         RAP1_IAA_30M (n=1: SRR6357076).
# Caveat, stated plainly: n=1 in the treatment arm means this demonstrates the
# STAR -> featureCounts -> DESeq2 mechanics, not a properly powered biological
# comparison. See README for how to scale to the full GSE110004 series.
suppressPackageStartupMessages({
  library(DESeq2)
  library(data.table)
})

args <- commandArgs(trailingOnly = TRUE)
fc_path <- ifelse(length(args) >= 1, args[1], "results/featurecounts.txt")
out_dir <- ifelse(length(args) >= 2, args[2], "results")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

fc <- fread(fc_path, skip = 1)
count_cols <- grep("Aligned\\.sortedByCoord\\.out\\.bam$", names(fc), value = TRUE)
sample_names <- sub(".*/(SRR[0-9]+)_Aligned.*", "\\1", count_cols)

cts <- as.matrix(fc[, ..count_cols])
rownames(cts) <- fc$Geneid
colnames(cts) <- sample_names

sample_condition <- c(
  SRR6357070 = "WT",
  SRR6357071 = "WT",
  SRR6357072 = "WT",
  SRR6357076 = "RAP1_IAA_30M"
)
coldata <- data.frame(
  condition = factor(sample_condition[colnames(cts)], levels = c("WT", "RAP1_IAA_30M"))
)
rownames(coldata) <- colnames(cts)

dds <- DESeqDataSetFromMatrix(countData = cts, colData = coldata, design = ~condition)
dds <- dds[rowSums(counts(dds)) >= 10, ]
dds <- DESeq(dds)
res <- results(dds, contrast = c("condition", "RAP1_IAA_30M", "WT"))
res_df <- as.data.frame(res)
res_df$gene <- rownames(res_df)
res_df <- res_df[order(res_df$padj), ]

fwrite(res_df, file.path(out_dir, "deseq2_results.tsv"), sep = "\t")

cat(sprintf(
  "DESeq2: %d genes tested after low-count filtering; %d with padj < 0.1\n",
  nrow(res_df), sum(res_df$padj < 0.1, na.rm = TRUE)
))
cat("\nTop 10 by adjusted p-value:\n")
print(head(res_df[, c("gene", "baseMean", "log2FoldChange", "pvalue", "padj")], 10))
