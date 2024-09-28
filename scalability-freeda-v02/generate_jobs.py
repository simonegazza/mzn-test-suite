#!/usr/bin/env python3

import itertools
import argparse
from pathlib import Path

REPETITIONS_PER_TEST = [3]
COMPONENTS = range(3, 50)
FLAVOURS = [3]
NODES = range(3, 50)
RESOURCES = [5]
COMPONENTS_GRAPH = ["barabasi_albert", "erdos_renyi", "path"]
INFRASTRUCTURE_GRAPH = ["barabasi_albert", "erdos_renyi", "complete", "ladder", "wheel"]

combinations = itertools.product(
    REPETITIONS_PER_TEST,
    COMPONENTS,
    FLAVOURS,
    NODES,
    RESOURCES,
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
        "-f " + str(f),
        "-n " + str(n),
        "-r " + str(r),
        "-g " + str(g),
        "-i " + str(i),
        "-o " + (
            Path(args.prefix)
            /
            f"c{c}_f{f}_n{n}_r{r}_g{g.split('_')[0]}_i{i.split('_')[0]}"
        )
    ))
    for t, c, f, n, r, g, i in combinations
]

print("\n".join(result))
