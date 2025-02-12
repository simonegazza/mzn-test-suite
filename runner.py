#!/usr/bin/env python

import subprocess, json, sys, argparse, re, os, traceback, resource, time
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
    "highs" # experimental solver
]

def format_float(number):
    return float("{:.3f}".format(number))

def print_to_file(data_file_name, solver_name, what):
    dzn_file_path = Path(data_file_name).absolute()
    dzn_name = str(os.path.basename(dzn_file_path))[:-4]
    output_file_name = dzn_file_path.parent / (dzn_name + "-" + solver_name + "-json.log")
    with open(output_file_name, "a") as f:
        f.write(what)

def pre_process():
    # Set nicing level
    os.nice(10)

    # Check every 5 minutes if there is less than one user on the machine
    minutes = 5
    while True:
        users = subprocess.run(
            "who | grep -v \"$(whoami)\"",
            stdout=subprocess.PIPE,
            text=True,
            shell=True
        )
        users = users.stdout.strip().split("\n")
        users_num = len(users) if users[0] else 0
        if users_num > 1:
            time.sleep(minutes * 60)
        else:
            break

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
                "--compiler-statistics",
                "-f", "-s", "-a", #-f = free search, -s = statistics, -a = all (even intermediate) solutions
                "-d", str(dzn_file_path),
                "--output-mode", "json", # This gives the object value under {}.json._objective
                "--output-objective",
                "--output-time", # This outputs time under every solution
                "--no-output-ozn",
                "--json-stream", # This makes the output a json, so it is parsable
                "--solver", solver_name,
                "--time-limit", str(timeout),
                str(Path(args.model).resolve())
            ]
            p = subprocess.Popen(
                " ".join(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                preexec_fn=pre_process
            )
            try:
                # Make sure process never goes over half RAM
                max_mem_allowed = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') // 2
                while p.poll() is None:
                    try:
                        result = subprocess.run("ps -o rss= -p " + str(p.pid), capture_output=True, text=True)
                        mem_used = int(result.stdout.strip()) * 1024 # Convert to bytes
                        if mem_used > max_mem_allowed:
                            p.kill()
                            raise Exception("Exceeded max memory usage")
                        time.sleep(5)
                    except:
                        time.sleep(1)
                        p.kill()
                        break

                output = p.stdout.read()
                if p.returncode != 0:
                    print(p.returncode)
                    dzn_name = str(os.path.basename(dzn_file_path))[:-4]
                    output_file_name = dzn_file_path.parent / (dzn_name + "-" + solver_name + "-run-error.log")
                    with open(output_file_name, "w") as f:
                        f.write(output)
                    raise Exception("MiniZinc failure")

                processes[solver_name] += [{"data_file": dzn, "process": output}]
            except Exception as e:
                print(
                    "Failure while running", dzn_file_path, "for solver", solver_name, "with reason", e,
                    file=sys.stderr
                )
                processes[solver_name] += [{
                    "data_file": dzn,
                    "process": p.stdout.read()
                }]
                continue

    results = {solver_name : [] for solver_name in processes.keys()}
    infs = re.compile("inf|-inf")
    for solver_name in processes.keys():
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

                json_rows = []
                for row in fixed_results:
                    try:
                        json_rows.append(json.loads(row))
                    except:
                        continue

                json_statistics = [j for j in json_rows if j["type"] == "statistics"]
                if len(json_statistics) == 0: # Compilation error
                    error_row = json_rows[-1]
                    results[solver_name] += [{
                        "problem" : str(process_description["data_file"]),
                        "status" : "COMPILATION_ERROR",
                        "what": error_row["what"] if "what" in error_row else "UNCAUGHT ERROR",
                        "message" : error_row["message"] if "message" in error_row else "???"
                    }]
                    continue

                json_compilation_statistics = json_statistics[0]
                flat_time = json_compilation_statistics["statistics"]["flatTime"]

                # Calculate amount of variables
                vars = sum(
                    v
                    for k, v in json_compilation_statistics["statistics"].items()
                    if "vars" in k.lower()
                )

                solutions = [r for r in json_rows if r["type"] == "solution"]
                objectives = {
                    format_float(s["time"] / 1000) : s["output"]["json"]["_objective"]
                    for s in solutions
                }

                try:
                    json_last_status = [j for j in json_rows if j["type"] == "status"][-1]
                    status = json_last_status["status"]
                    solve_time = json_last_status["time"] / 1000
                except:
                    status = "SATISFIABLE" if len(objectives) != 0 else "UNKNOWN"
                    json_solve_times = [j for j in json_statistics if "solveTime" in j["statistics"]]
                    if len(json_solve_times) > 0:
                        solve_time = json_solve_times[-1]["statistics"]["solveTime"]
                    else:
                        solve_time = timeout

                if len([j for j in json_rows if j["type"] == "error"]) > 0:
                    print_to_file(process_description["data_file"], solver_name, process_description["process"])

                results[solver_name] += [{
                    "problem" : str(process_description["data_file"]),
                    "status" : status,
                    "flat_time" : format_float(flat_time),
                    "solve_time" : solve_time,
                    "objectives" : objectives,
                    "flatzinc_vars" : vars
                }]
            except Exception as e:
                # Something went very wrong during json readings. So wring that
                # my failure recover above did not worked
                print(
                    "Error while processing",
                    process_description["data_file"],
                    "for solver",
                    solver_name,
                    file=sys.stderr
                )
                print(traceback.print_exc(), file=sys.stderr)

                # Save failed result into a file to later use
                print_to_file(process_description["data_file"], solver_name, process_description["process"])
                continue

    # Be sure to save a into a file, even if a folder is set
    statistics_location = Path(args.statistics_location)
    if os.path.isdir(statistics_location):
        statistics_location = statistics_location / "results.json"
    # Save statistics json
    with open(statistics_location, 'w') as f:
        json.dump(results, f, indent=4)
