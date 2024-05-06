#!/usr/bin/env python

import sys, argparse, os, subprocess, fcntl, json, re
from pathlib import Path

def format_float(number):
    return float("{:.3f}".format(number))

def make_args():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Runs previously generated job file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "job_path",
        help="""
        location of the job file that must contain the following columns:
            1. problem_id
            2. solver
            3. mzn file path
            4. dzn data path
        """,
        type=str,
        metavar="job file path"
    )
    parser.add_argument(
        "-v",
        "--version",
        action='version',
        version='%(prog)s 1.0'
    )
    parser.add_argument(
        "-l",
        "--statistics-location",
        help="file path to store result's statistics (this must be accessible to all machines)",
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
    parser.add_argument(
        "-w",
        "--window-size",
        help="How many job this machine should take at once",
        metavar="P",
        type=int,
        default=os.cpu_count()
    )
    return parser.parse_args()

def group_stats(processes):
    unsats = 0
    results = {solver_name : [] for solver_name in processes.keys()}
    for solver_name in processes.keys():
        for process_description in processes[solver_name]:
            print("Processing results of", str(process_description["data_file"]))
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
            json_rows = [j for j in json_rows if j["type"] != "comment"]
            json_rows = json_rows[:-1]

            flat_time = json_rows[0]["statistics"]["flatTime"]
            status = json_rows[-2]["status"] if "status" in json_rows[-2] else "UNKNOWN"

            solutions = [r for r in json_rows if r["type"] == "solution"]

            if status == "UNSATISFIABLE":
                objectives = {
                    format_float(json_rows[-1]["statistics"]["solveTime"]) : None
                }
                unsats += 1
            else: # Either UNKNOWN or SATISFIED or OPTIMAL_SOLUTION
                if len(solutions) > 0:
                    objectives = {
                        format_float(s["time"] / 1000) : s["output"]["json"]["_objective"]
                        for s in solutions
                    }
                else:
                    objectives = {timeout : None}

            results[solver_name] += [{
                "problem" : str(process_description["data_file"]),
                "status" : status,
                "flat_time" : format_float(flat_time),
                "objectives" : objectives
            }]

    return results, unsats

if __name__ == '__main__':
    args = make_args()
    timeout = str(args.timeout * 1000 * 60)

    jobs_path = Path(args.job_path)
    if not jobs_path.is_file():
        print("Jobs path must be a valid file path")
        exit()

    processes = {}
    ids = []
    # Until there is a job to do
    while os.path.getsize(jobs_path) > 0:
        with open(jobs_path, "r+") as f:
            # Acquire exclusive lock on file to block other when reading
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            # Get at most args.window_size jobs
            lines = f.readlines()
            f.seek(0)

            jobs = lines[:args.window_size]

            # If there are no more jobs then make this file empty
            if len(lines[args.window_size:]) > 0:
                f.write("".join(lines[args.window_size:]))
            else:
                f.write("")
            f.truncate()

            fcntl.flock(f.fileno(), fcntl.LOCK_UN) # Release lock on file

        for line in jobs:
            print(line.strip())
            job = [e.strip().replace("\n", "") for e in line.split(",")]
            command = [
                "minizinc",
                "-f", "-s", "-a", #-f = free search, -s = statistics, -a = all (even intermediate) solutions
                "-d", Path(job[2]).absolute(),
                "--output-mode", "json", # This gives the object value under {}.json._objective
                "--output-objective",
                "--output-time", # This outputs time under every solution
                "--no-output-ozn",
                "--json-stream", # This makes the output a json, so it is parsable
                "--solver", job[0],
                "--time-limit", timeout,
                Path(job[1]).absolute()
            ]
            ids += [job[2]]

            p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE
            )
            p.wait()  # await the processes to finish before starting the next one
            if job[0] in processes:
                processes[job[0]] += [{"data_file": job[2], "process": p}]
            else:
                processes[job[0]] = [{"data_file": job[2], "process": p}]

        # Be sure to save a into a file, even if a folder is set
        result_location = Path(args.statistics_location)
        if os.path.isdir(result_location):
            result_location = result_location / "results.json"

        # Group and save results
        total_unsats = 0
        with open(result_location, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX) # Acquire exclusive lock on file

            # Load previously generated results
            previous_results = json.load(f) if os.path.getsize(result_location) > 0 else {}
            f.seek(0)

            # Compute results and reset
            current_results, unsats = group_stats(processes)
            processes = {}

            total_unsats += unsats

            # Update previous results
            for k in current_results.keys():
                if k in previous_results:
                    previous_results[k] += current_results[k]
                else:
                    previous_results.update({k : current_results[k]})

            # Save onto file
            json.dump(previous_results, f, indent=4)
            f.truncate()

            fcntl.flock(f.fileno(), fcntl.LOCK_UN) # Release lock on file

    print("Unsat ratio for", ', '.join(ids), ":", format_float(total_unsats / len(ids)))
