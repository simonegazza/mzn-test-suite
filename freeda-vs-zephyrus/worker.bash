#!/usr/bin/bash

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

    mkdir -p $location/{freeda,zephyrus}

    python3 /path/to/Python-parser/generator/scalability/zephyrus_generator.py $job

    python3 /path/to/mzn-test-suite/runner.py \
        /path/to/mzn-test-suite/freeda-vs-zephyrus/freeda-model-v0.2.1.mzn \
        $location/freeda \
        -s highs gecode chuffed cpsatlp \
        -t 5 \
        -l $location/freeda/$(basename $location)-freeda-result.json

    python3 /path/to/mzn-test-suite/runner.py \
        /path/to/mzn-test-suite/freeda-vs-zephyrus/zephyrus.mzn \
        $location/zephyrus \
        -s highs gecode chuffed cpsatlp \
        -t 5 \
        -l $location/zephyrus/$(basename $location)-zephyrus-result.json

done
