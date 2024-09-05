#!/bin/bash
#SBATCH --job-name=minizinc_cluster_runner
#SBATCH --mem=1G
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=ALL
#SBATCH --mail-user=
#SBATCH --output=scalability_freeda_v02_-%a.log
#SBATCH --error=scalability_freeda_v02_-%a.error

job=$(sed -n "$SLURM_ARRAY_TASK_ID"p $1)
comps=$(echo $job | sed 's/\-.*$//g')
nodes=$(echo $job | sed 's/^.*\-//g')

# path/to/Python-parser/generator.py 3 \
#     -c $comps \
#     -n $nodes \
#     -f 3 \
#     -r 5 \
#     -o /path/to/data/dzns/c${comps}_f3_n${nodes}_r5/

# path/to/mzn-test-suite/runner.py \
#     path/to/mzn-test-suite/scalability-freeda-v02/freeda-model-v0.2.mzn \
#     path/to/data/dzns/c${comps}_f3_n${nodes}_r5/ \
#     -s highs gecode chuffed cpsatlp \
#     -t 5 \
#     -l /path/to/data/results/c${comps}_f3_n${nodes}_r5-result.json
