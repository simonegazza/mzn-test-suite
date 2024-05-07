#!/usr/bin/env bash

# USAGE: ./execute.bash model location
# Where amount is the number of files to generate and location is where to save
# generated files and statistics

./runner.py $1 $2 -l $2
./stats.py $2/results.json
