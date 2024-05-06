#!/usr/bin/env bash

# USAGE: ./execute.bash model amount location
# Where amount is the number of files to generate and location is where to save
# generated files and statistics

./generator.py $2 -l $3
./runner.py $1 $3 -l $3
./stats.py $3/results.json
