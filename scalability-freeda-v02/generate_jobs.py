#!/usr/bin/env python3

import itertools
import argparse

def parse_args(raw_args=None):
    parser = argparse.ArgumentParser(description="Job file generator")
    parser.add_argument("amount", metavar="n", type=int, help="Generate n x n jobs")
    parser.add_argument(
        "--separator",
        "-s",
        type=str,
        default="-",
        help="Separator between component and node",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Where to locate the job file",
    )
    args = parser.parse_args(raw_args)

    return args

def main(raw_args=None):
    args = parse_args(raw_args)
    result = [
        str(c) + args.separator + str(n)
        for c, n in itertools.product(
            range(1, args.amount + 1),
            range(1, args.amount + 1))
    ]

    result = '\n'.join(result)

    if args.output is None:
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)


if __name__ == "__main__":
    main()
