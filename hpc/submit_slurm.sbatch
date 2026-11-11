#!/bin/bash
#SBATCH --job-name=bulk-rnaseq-star-deseq2
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
# Edit for your site: partition/account, and `module load` names.
##SBATCH --partition=compute
##SBATCH --account=YOUR_ACCOUNT
#
# Submit from the repository root:  mkdir -p logs && sbatch hpc/submit_slurm.sbatch
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"

# Site modules (names vary; failures are ignored if the tool is already on PATH).
module load apptainer 2>/dev/null || module load singularity 2>/dev/null || true

# Docker is not permitted on most clusters: rules run through Apptainer instead.
export CONTAINER_RUNTIME=apptainer
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-${SCRATCH:-$HOME}/.apptainer}"

# Host tools (snakemake + SLURM executor plugin + natively-run tools) come from conda.
# One-time: micromamba create -y -n wf -f environment.yml
set +u  # conda activation scripts reference unset variables
eval "$(micromamba shell hook -s bash)" 2>/dev/null || true
micromamba activate wf 2>/dev/null || conda activate wf
set -u

# Run `bash hpc/prefetch.sh` on a login node first if compute nodes have no internet.
# This head job submits each rule as its own SLURM job (see workflow/profiles/slurm).
snakemake -s workflow/Snakefile --workflow-profile workflow/profiles/slurm
