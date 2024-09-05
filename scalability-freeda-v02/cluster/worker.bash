#!/usr/bin/bash

while [ $(wc -l < jobs.txt) -ge 0 ]; do

    # Await for the lock file to be removed
    lockfile=$(dirname $1)/.lock
    while [ -e $lockfile ];
    do
        sleep 1
    done
    echo $(hostname) - Acquiring lock

    # Make lock, take data, change jobs file, remove the lock
    touch $lockfile
    job=$(head -n 1 $1)
    sed -i '1d' $1
    rm $lockfile

    # Extract job info
    comps=$(echo $job | sed 's/\-.*$//g')
    nodes=$(echo $job | sed 's/^.*\-//g')

    # Run the jobs
    echo $(hostname) - running ${comps}x${nodes}

    mkdir -p /path/to/data/dzns/c${comps}_f3_n${nodes}_r5/

    python3 /path/to/Python-parser/generator/scalability/generator.py 3 \
        -c $comps \
        -n $nodes \
        -f 3 \
        -r 5 \
        -o /path/to/data/dzns/c${comps}_f3_n${nodes}_r5/

    python3 /path/to/mzn-test-suite/runner.py \
        /path/to/mzn-test-suite/scalability-freeda-v02/freeda-model-v0.2.mzn \
        /path/to/data/dzns/c${comps}_f3_n${nodes}_r5/ \
        -s highs gecode chuffed cpsatlp \
        -t 5 \
        -l /path/to/data/results/c${comps}_f3_n${nodes}_r5-result.json

    echo $(hostname) - done for ${comps}x${nodes}
done

echo "$(hostname) - done"
