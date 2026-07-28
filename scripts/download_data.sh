#!/bin/bash
# Fetches paired-end FASTQ subsets + a matching genome/GTF subset from
# nf-core/test-datasets (rnaseq branch), derived from GSE110004 (Challal et
# al., Molecular Cell 2018). Small by design -- see README for why.
set -euo pipefail
cd "$(dirname "$0")/.."

FASTQ_BASE="https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004"
REF_BASE="https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq3/reference"

mkdir -p data/fastq data/reference

for f in SRR6357070_1 SRR6357070_2 SRR6357071_1 SRR6357071_2 \
         SRR6357072_1 SRR6357072_2 SRR6357076_1 SRR6357076_2; do
  out="data/fastq/${f}.fastq.gz"
  if [ -f "$out" ]; then
    echo "Already downloaded: $out"
    continue
  fi
  echo "Downloading $out"
  curl -sL --fail -o "$out" "${FASTQ_BASE}/${f}.fastq.gz"
done

if [ ! -f data/reference/genome.fasta ]; then
  echo "Downloading reference genome"
  curl -sL --fail -o data/reference/genome.fasta "${REF_BASE}/genome.fasta"
fi

if [ ! -f data/reference/genes.gtf ]; then
  echo "Downloading reference GTF"
  curl -sL --fail -o data/reference/genes.gtf.gz "${REF_BASE}/genes.gtf.gz"
  gunzip -f data/reference/genes.gtf.gz
fi

echo "Done. $(ls data/fastq | wc -l) FASTQ files, reference genome + GTF ready."
