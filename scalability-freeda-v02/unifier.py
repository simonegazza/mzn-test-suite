#!/usr/bin/env python3

import json
from pathlib import Path
import argparse

def parse_args(raw_args=None):
    parser = argparse.ArgumentParser(
        prog="Compress results file",
        description="Compress files into a single one from previously run results",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "folder",
        help="folder in which results are stored",
        type=str
    )
    parser.add_argument(
        "--output",
        "-o",
        help="location where to store file",
        type=str,
        default=None
    )
    args = parser.parse_args()
    return args

def main(raw_args=None):
    args = parse_args(raw_args=raw_args)

    results_path = Path(args.folder)

    results = []
    for results_file in results_path.rglob('*-result.json'):
        with open(results_file, "r") as f:
            results.append(json.load(f))

    keys = {r for j in results for r in j.keys()}

    final = {k : [] for k in keys}
    for k in keys:
        for j in results:
            final[k] += j[k]

    if args.output is None:
        print(final)
    else:
        with open(args.output, "w") as f:
            json.dump(final, f)

if __name__ == "__main__":
    main()
