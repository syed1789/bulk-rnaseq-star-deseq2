# Running on HPC (SLURM) and AWS

Scripts and settings below were validated locally (see "What was verified").

The `deseq2`, `load_sqlite` and `spark_aggregate` rules run natively (R/DESeq2, Python, PySpark+Java); `environment.yml` provides them.

## HPC (SLURM + Apptainer)

Docker is not permitted on most clusters, so the Snakefile has a runtime
switch: `CONTAINER_RUNTIME=docker` (default, unchanged) or `apptainer`.

```bash
# one-time, on a login node
micromamba create -y -n wf -f environment.yml
bash hpc/prefetch.sh            # caches images, downloads input data
# edit slurm_partition / account in workflow/profiles/slurm/config.yaml
mkdir -p logs && sbatch hpc/submit_slurm.sbatch
```

The sbatch script is a small head job that runs Snakemake with the SLURM
executor profile; each rule becomes its own SLURM job.

## AWS (single EC2 instance + S3)

One-shot instance: boots Amazon Linux 2023, installs Docker, clones this repo,
runs the analysis, syncs outputs to S3, then **terminates itself** (a
`shutdown -h +MAX_HOURS` dead-man switch also guards against hangs).

```bash
export S3_BUCKET=my-bucket          # existing bucket you can write to
export INSTANCE_PROFILE=my-ec2-role # IAM instance profile allowing s3:PutObject
./aws/launch_ec2.sh
```

Default instance `m6i.2xlarge` (100 GB gp3). Outputs land in
`s3://$S3_BUCKET/bulk-rnaseq-star-deseq2/<timestamp>/`, with `analysis.log`. Remember to
check cost for your instance type and region; nothing is created until you run
the script, and the instance stops billing when it terminates.

## What was verified

- `snakemake -n -p` dry-run output with the default (Docker) runtime is identical to the pre-change output.
- With `CONTAINER_RUNTIME=apptainer` the dry run emits only `apptainer exec` commands.
- Shell scripts pass `bash -n` and shellcheck.
