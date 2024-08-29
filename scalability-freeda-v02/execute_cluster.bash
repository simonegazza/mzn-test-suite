#!/usr/bin/env bash

NUM_JOBS=$(wc -l < $1)

TOTAL_MINUTES=$(($NUM_JOBS * 16))

sbatch --time=$TOTAL_MINUTES --array=1-${NUM_JOBS} /path/to/execute.slurm "$1"
