#!/usr/bin/env bash
# Run on a login node (internet access) so compute nodes can use the cache.
set -euo pipefail
cd "$(dirname "$0")/.."
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-${SCRATCH:-$HOME}/.apptainer}"
module load apptainer 2>/dev/null || module load singularity 2>/dev/null || true
for img in \
  "quay.io/biocontainers/star:2.7.11b--h5ca1c30_8" \
  "quay.io/biocontainers/subread:2.0.8--h577a1d6_0"
do
  echo "Caching $img"
  apptainer exec "docker://$img" true
done
bash scripts/download_data.sh
