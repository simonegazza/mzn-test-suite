#!/usr/bin/bash

# Project path folder without an ending slash
general_path=/path/to/this/parent/folder

lockfile=$(dirname $1)/.lock

while [ $(wc -l < jobs.txt) -ge 0 ]; do

    # Await for the lock file to be removed
    while [ -e $lockfile ];
    do
        sleep 1
    done

    # Make lock, take data, change jobs file, remove the lock
    touch $lockfile
    job=$(head -n 1 $1)
    sed -i '1d' $1
    rm $lockfile

    # Extract location
    location=$(echo $job | sed 's/^.*\-o //g')

    mkdir -p $location

    python3 $general_path/Python-parser/generator/scalability/generator.py $job

    python3 $general_path/mzn-test-suite/runner.py \
        $general_path/mzn-test-suite/scalability-freeda-v02/freeda-model-v0.2.mzn \
        $location \
        -s highs gecode chuffed cpsatlp \
        -t 5 \
        -l $location/$(basename $location)-result.json

done
