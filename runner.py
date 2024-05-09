#!/usr/bin/env python

import subprocess, json, sys, argparse, re, os
from pathlib import Path

# Possible solvers
SOLVERS = [
    # Default ones
    "coinbc",
    "chuffed",
    "gecode",
    "cpsatlp", # ortools

    # Others
    "cplex",
    "gurobi",
    "scip",
    "xpress",
    "highs" # apparently this is bugged
]

def format_float(number):
    return float("{:.3f}".format(number))

def make_parseargs():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Runs previously generated dzn files using a known MiniZinc model template',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "model",
        help="model file location",
        type=str
    )
    parser.add_argument(
        "dzn",
        help="location where dzn files could be found",
        type=str,
        metavar="dzn folder path"
    )
    parser.add_argument(
        "-v",
        "--version",
        action='version',
        version='%(prog)s 1.0'
    )
    parser.add_argument(
        "-s",
        "--solvers",
        help="solvers to use",
        default=SOLVERS[0:4],
        metavar="solver_list",
        choices=SOLVERS,
        nargs='+'
    )
    parser.add_argument(
        "-l",
        "--statistics-location",
        help="file path to store result's statistics",
        type=str,
        metavar="path",
        default="./results.json"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help="timeout in minutes per problem",
        metavar="T",
        type=float,
        default=5.0
    )
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = make_parseargs()
    timeout = str(args.timeout * 1000 * 60)

    data_files = [f for f in Path(args.dzn).rglob("*.dzn")]

    processes = {}
    for solver_name in args.solvers:
        processes[solver_name] = []
        for dzn in data_files:
            command = [
                "minizinc",
                "-f", "-s", "-a", #-f = free search, -s = statistics, -a = all (even intermediate) solutions
                "-d", Path(dzn).absolute(),
                "--output-mode", "json", # This gives the object value under {}.json._objective
                "--output-objective",
                "--output-time", # This outputs time under every solution
                "--no-output-ozn",
                "--json-stream", # This makes the output a json, so it is parsable
                "--solver", solver_name,
                "--time-limit", timeout,
                Path(args.model).absolute()
            ]

            p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE
            )
            p.wait()  # await the processes to finish before starting the next one
            processes[solver_name] += [{"data_file": dzn, "process": p}]

    results = {solver_name : [] for solver_name in processes.keys()}
    for solver_name in processes.keys():
        total_unsats = 0
        for process_description in processes[solver_name]:
            p = process_description["process"]
            json_rows = [
                json.loads(
                    re.sub(
                        "inf|-inf", # This bug costed me several hours
                        lambda x: '"inf"' if x.group(0) == "inf" else '"-inf"',
                        r.decode("utf-8").strip()
                    )
                )
                for r in p.stdout.readlines()
            ]
            json_first_statistics = [j for j in json_rows if j["type"] == "statistics"][0]
            json_last_status = [j for j in json_rows if j["type"] == "status"][-1]

            status = json_last_status["status"]
            solve_time = json_last_status["time"] / 1000
            flat_time = json_first_statistics["statistics"]["flatTime"]
            solutions = [r for r in json_rows if r["type"] == "solution"]

            if status == "UNSATISFIABLE":
                objectives = {}
                total_unsats += 1
            elif status == "UNKNOWN":
                objectives = {timeout : None}
            else:
                objectives = {
                    format_float(s["time"] / 1000) : s["output"]["json"]["_objective"]
                    for s in solutions
                }

            results[solver_name] += [{
                "problem" : str(process_description["data_file"]),
                "status" : status,
                "flat_time" : format_float(flat_time),
                "solve_time" : solve_time,
                "objectives" : objectives
            }]

        print(
            "Unsats ratio for",
            solver_name,
            ":",
            format_float(total_unsats / len(processes[solver_name]))
        )

    # Be sure to save a into a file, even if a folder is set
    statistics_location = Path(args.statistics_location)
    if os.path.isdir(statistics_location):
        statistics_location = statistics_location / "results.json"
    # Save statistics json
    with open(statistics_location, 'w') as f:
        json.dump(results, f, indent=4)
