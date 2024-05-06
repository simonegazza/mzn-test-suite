#!/usr/bin/env python

import argparse, sys, math, json, importlib.util
from pathlib import Path

def get_data_file_path(folder_path : str, i : int, amount : int):
    return folder_path / (
        "data-" + str(i).zfill(math.ceil(math.log10(amount))) + ".dzn"
    )

def make_args():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="""Generates a specified number of dzn configurations based
        on input parameters. \nThe program allows customization of the function to
        call and the location to save the generated files.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "N",
        help="number of files to generate per solver",
        type=int,
        default="10"
    )
    parser.add_argument(
        "-v",
        "--version",
        action='version',
        version='%(prog)s 1.0'
    )
    parser.add_argument(
        "-l",
        "--location",
        metavar="path",
        help="location to store generated files",
        type=str,
        default="./data"
    )
    parser.add_argument(
        "-g",
        "--generate-function",
        metavar="path",
        help="location where the function 'generate' resides",
        type=str,
        default="./utils.py"
    )
    parser.add_argument(
        "-a",
        "--args",
        metavar="path",
        help="location to a JSON containing a list of arguments to pass to the 'generate' function",
        type=str
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = make_args()

    if args.args is not None:
        with open(Path(args.a), 'r') as f:
            arguments = json.load(f)
    else:
        arguments = [{} for _ in range(args.N)]

    try:
        spec = importlib.util.spec_from_file_location("generator", Path(args.generate_function))
        generator = importlib.util.module_from_spec(spec)
        sys.modules["generator"] = generator
        spec.loader.exec_module(generator)
    except Exception as e:
        print("Unable to find", args.generate_function, "file")
        print(e)
        exit()

    data = [
        generator.generate(**json_args)
        for _, json_args in zip(range(args.N), arguments)
    ]

    # Create saving location and files
    folder_path = Path(args.location)
    folder_path.mkdir(parents=True, exist_ok=True)
    for d, i in zip(data, range(args.N)):
        file_path = get_data_file_path(folder_path, i, args.N)
        with open(file_path, 'w') as f:
            f.write(d)
