#!/usr/bin/env python3

import itertools
import argparse
from pathlib import Path

REPETITIONS_PER_TEST = [3]
COMPONENTS = range(4, 33)
#FLAVOURS = [1]
NODES = range(3, 33)
#RESOURCES = [1]
COMPONENTS_GRAPH = ["barabasi_albert", "erdos_renyi", "path"]
INFRASTRUCTURE_GRAPH = ["complete"]

combinations = itertools.product(
    REPETITIONS_PER_TEST,
    COMPONENTS,
    NODES,
    COMPONENTS_GRAPH,
    INFRASTRUCTURE_GRAPH
)

parser = argparse.ArgumentParser(description="Generate job file.")
parser.add_argument("-p", "--prefix", type=str, help="Prefix location to output files", default="./")
args = parser.parse_args()


result = [
    " ".join((
        str(t),
        "-c " + str(c),
        "-n " + str(n),
        "-g " + str(g),
        "-i " + str(i),
        "-o " + str(
            Path(args.prefix)
            /
            f"c{c}_n{n}_g{g.split('_')[0]}_i{i.split('_')[0]}"
        )
    ))
    for t, c, n, g, i in combinations
]

print("\n".join(result))
