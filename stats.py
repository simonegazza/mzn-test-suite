#!/usr/bin/env python

import argparse, sys, json, itertools
from pathlib import Path

def round_down(x):
    return int(float(x))

def format_float(number):
    return "{:.3f}".format(number)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Compute the best solver from a previously generate challenge',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "location",
        help="path of previously run challenges",
        type=str
    )
    parser.add_argument(
        "-v",
        "--version",
        action='version',
        version='%(prog)s 1.0'
    )
    args = parser.parse_args()

    with open(Path(args.location), 'r') as f:
        challenge_stats = json.load(f)

    solvers = set(challenge_stats.keys())

    result = {}
    for solver_name, solutions in challenge_stats.items():
        optimal_solutions = 0
        unsats = 0
        sats = 0
        optimization_time_sum = 0
        flat_time_sum = 0
        time_first_solution = 0
        for solution in solutions:
            flat_time_sum += solution["flat_time"]
            if solution["status"] == "OPTIMAL_SOLUTION":
                optimal_solutions += 1
                optimization_time_sum += solution["solve_time"] + solution["flat_time"]
                time_first_solution += float(min(
                    solution["objectives"].items(),
                    key=lambda v : v[1]
                )[0])
            elif solution["status"] == "UNSATISFIABLE":
                time_first_solution += solution["solve_time"] + solution["flat_time"]
                unsats += 1
            elif solution["status"] == "SATISFIED":
                time_first_solution += float(min(
                    solution["objectives"].items(),
                    key=lambda v : v[1]
                )[0])
                sats += 1

        result.update({
            solver_name : {
                "optimals" : optimal_solutions,
                "unsats" : unsats,
                "sats" : sats,
                "average_time_to_first_solution" : format_float(
                    time_first_solution / len(solutions)
                ),
                "average_optimization_time" : format_float(
                    optimization_time_sum / optimal_solutions
                ),
                "average_flattening_time" : format_float(
                    flat_time_sum / len(solutions)
                )
        }})

    # Calculate minizinc challenge values
    # Get solvers couples (as unordered couples) without repetitions
    points = {s : 0 for s in solvers}
    solver_combinations = set(itertools.combinations(solvers, r=2))
    problems = {p["problem"] for s in challenge_stats.values() for p in s}
    for s1, s2 in solver_combinations:
        for problem_name in problems:
            p1 = [p for p in challenge_stats[s1] if p["problem"] == problem_name][0]
            p2 = [p for p in challenge_stats[s2] if p["problem"] == problem_name][0]

            # ┌─────────────┬───────────┬─────────────┬────────────┬───────────┐
            # │     s1 \ s2 │ satisfied │ unsatisfied │     unkown │ optimized │
            # ├─────────────┼───────────┼─────────────┼────────────┼───────────┤
            # │   satisfied │         ? │           x │         s1 │        s2 │
            # ├─────────────┼───────────┼─────────────┼────────────┼───────────┤
            # │ unsatisfied │         x │           ? │         s1 │         x │
            # ├─────────────┼───────────┼─────────────┼────────────┼───────────┤
            # │      unkown │        s2 │          s2 │  0.5 - 0.5 │        s2 │
            # ├─────────────┼───────────┼─────────────┼────────────┼───────────┤
            # │   optimized │        s1 │           x │         s1 │         ? │
            # └─────────────┴───────────┴─────────────┴────────────┴───────────┘

            statuses = set((p1["status"], p2["status"]))

            if len(statuses) == 2: # Not on the diagonal
                if "UNSATISFIABLE" in statuses:
                    print(
                        "WARNING:",
                        s1 if p1["status"] == "UNSATISFIABLE" else s2,
                        "returned UNSATISFIABLE but",
                        s2 if p1["status"] == "UNSATISFIABLE" else s1,
                        "returned",
                        p2["status"] if p1["status"] == "UNSATISFIABLE" else p1["status"],
                        "on",
                        p1["problem"] + ",",
                        "plese subtract one from the total available score of",
                        len(problems) * len(solver_combinations),
                        file=sys.stderr
                    )
                    continue
                elif "UNKNOWN" in statuses:
                    points[s2 if p1["status"] == "UNKNOWN" else s1] += 1
                elif "OPTIMAL_SOLUTION" in statuses:
                    points[s1 if p1["status"] == "OPTIMAL_SOLUTION" else s2] += 1
            else: # On the diagonal
                if "UNKNOWN" in statuses:
                    points1 = 0.5
                    points2 = 0.5
                elif statuses == {"SATISFIED"}:
                    p1_greatest_key = max(p1["objectives"].keys(), key=lambda x : float(x))
                    p2_greatest_key = max(p2["objectives"].keys(), key=lambda x : float(x))
                    p1_object_value = p1["objectives"][p1_greatest_key]
                    p2_object_value = p2["objectives"][p2_greatest_key]
                    if p1_object_value != p2_object_value:
                        points1 = 1 if p1_object_value > p2_object_value else 0
                        points2 = 0 if p1_object_value > p2_object_value else 1
                    else:
                        t1 = round_down(p1_greatest_key) + p1["flat_time"]
                        t2 = round_down(p2_greatest_key) + p2["flat_time"]
                        if t1 == t2:
                            points1 = 0.5
                            points2 = 0.5
                        else:
                            points1 = 0 if t1 > t2 else 1
                            points2 = 1 if t1 > t2 else 0
                else: # UNSATISFIABLE or OPTIMAL_SOLUTION
                    t1 = round_down(p1["solve_time"]) + p1["flat_time"]
                    t2 = round_down(p2["solve_time"]) + p2["flat_time"]
                    if t1 == t2:
                        points1 = 0.5
                        points2 = 0.5
                    else:
                        points1 = t2 / (t1 + t2)
                        points2 = t1 / (t1 + t2)

                points[s1] += points1
                points[s2] += points2

    for s, p in points.items():
        result[s].update({"points" : format_float(p)})

    print(json.dumps(result, indent=4))
