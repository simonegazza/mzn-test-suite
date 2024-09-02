#!/usr/bin/env python

import subprocess, json, sys, argparse, re, os, traceback
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
    timeout = int(args.timeout * 1000 * 60)

    data_files = [f for f in Path(args.dzn).rglob("*.dzn")]

    processes = {}
    for solver_name in args.solvers:
        processes[solver_name] = []
        for dzn in data_files:
            dzn_file_path = Path(dzn).absolute()
            command = [
                "minizinc",
                "-f", "-s", "-a", #-f = free search, -s = statistics, -a = all (even intermediate) solutions
                "-d", dzn_file_path,
                "--output-mode", "json", # This gives the object value under {}.json._objective
                "--output-objective",
                "--output-time", # This outputs time under every solution
                "--no-output-ozn",
                "--json-stream", # This makes the output a json, so it is parsable
                "--solver", solver_name,
                "--time-limit", str(timeout),
                Path(args.model).resolve()
            ]
            try:
                p = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    text=True
                )

                process_output = p.stdout
                if p.returncode != 0:
                    dzn_name = str(os.path.basename(dzn_file_path))[:-4]
                    output_file_name = dzn_file_path.parent / (dzn_name + "-" + solver_name + "-run-error.log")
                    with open(output_file_name, "w") as f:
                        f.write(process_output)
                    raise Exception()

                processes[solver_name] += [{"data_file": dzn, "process": process_output}]
            except:
                print(
                    "Failure while running", dzn_file_path, "for solver", solver_name,
                    file=sys.stderr
                )
                continue

    results = {solver_name : [] for solver_name in processes.keys()}
    infs = re.compile("inf|-inf")
    for solver_name in processes.keys():
        total_unsats = 0
        total_unknowns = 0
        for process_description in processes[solver_name]:
            try:
                # The output of MiniZinc is sometimes a mess, clean it
                fixed_results = [x for x in process_description["process"].split("\n") if len(x) > 0]
                fixed_results = [x for x in fixed_results if x != "{}"]
                fixed_results = [x.strip() for x in fixed_results]
                # Also this bug costed me several hours; seems to be fixed after
                # version 2.8.5 of MiniZinc
                fixed_results = [
                    infs.sub(lambda x: '"inf"' if x.group(0) == "inf" else '"-inf"', x)
                    for x in fixed_results
                ]
                json_rows = [json.loads(x) for x in fixed_results]
                json_first_statistics = [j for j in json_rows if j["type"] == "statistics"][0]
                try:
                    json_last_status = [j for j in json_rows if j["type"] == "status"][-1]
                except:
                    json_last_status = {"status" : "UNKNOWN", "time": timeout / 1000}

                status = json_last_status["status"]
                solve_time = json_last_status["time"] / 1000
                flat_time = json_first_statistics["statistics"]["flatTime"]
                solutions = [r for r in json_rows if r["type"] == "solution"]

                objectives = {
                    format_float(s["time"] / 1000) : s["output"]["json"]["_objective"]
                    for s in solutions
                }

                if status == "UNSATISFIABLE":
                    total_unsats += 1
                if status == "UNKNOWN":
                    total_unknowns += 1

                results[solver_name] += [{
                    "problem" : str(process_description["data_file"]),
                    "status" : status,
                    "flat_time" : format_float(flat_time),
                    "solve_time" : solve_time,
                    "objectives" : objectives
                }]
            except Exception as e:
                print(
                    "Error while processing",
                    process_description["data_file"],
                    "for solver",
                    solver_name,
                    file=sys.stderr
                )
                print(traceback.print_exc(), file=sys.stderr)

                # Save failed result into a file to later use
                dzn_file_path = Path(process_description["data_file"]).absolute()
                dzn_name = str(os.path.basename(dzn_file_path))[:-4]
                output_file_name = dzn_file_path.parent / (dzn_name + "-" + solver_name + "-json.log")
                with open(output_file_name, "w") as f:
                    f.write(process_output)
                continue

        for name, ratio in zip(("unsat", "unkown"), (total_unsats, total_unknowns)):
            r = format_float(ratio / len(processes[solver_name]))
            print(name, "ratio for", solver_name, ":", r, "\n")

    # Be sure to save a into a file, even if a folder is set
    statistics_location = Path(args.statistics_location)
    if os.path.isdir(statistics_location):
        statistics_location = statistics_location / "results.json"
    # Save statistics json
    with open(statistics_location, 'w') as f:
        json.dump(results, f, indent=4)
