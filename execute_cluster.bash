#!/usr/bin/env bash

set -e

# USAGE: ./execute_cluster.bash model amount location machine_list
# Where:
# - model is the model to run
# - amount is the number of files to generate
# - location is where to save generated files (like logs and errors) and
#   statistics
# - machine_list is a list of machines in which to run the script

amount="$(expr $2 - 1)"

# Generate data files
echo "GENERATING FILES"
./generator.py $amount -l $3

# Generate jobs file and shuffle rows
echo "GENERATING JOB FILE"
for s in "gecode" "chuffed" "highs"; do
    for i in `seq -w 0 $amount`; do
        echo "$s, $1, $3/data-$i.dzn";
    done;
done | shuf > $3/jobs.csv

echo "RUNNING JOB FILE"
for m in `cat $4`; do
    ./cluster_runner.py $3/jobs.csv -l $3/results.json > $3/$m.log 2>&1
done

echo "GENERATING STATISTICS"
./stats.py $3/results.json > $3/points.json

echo "DONE"
