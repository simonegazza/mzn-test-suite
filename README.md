# Requirements
- python >= 3.11
- MiniZinc >= 2.8.3 (solvers: OR Tools CP SAT 9.8.3296, COIN-BC 2.10.11/1.17.9,
  Gecode 6.3.0, Chuffed 0.13.1)
- being inside this folder

# Run the script
There are 4 scripts that you can run. The `*.py` files have a `--help` option
that you can use as help message.
To run the scripts you can call them via `./` notation or python notation (for
exaple the `generator.py` file can be called via: `python generator.py` or via
`./generator.py`)

# Flow
To generate and run the test locally, you should call the following scripts one
after the other:
- `generator.py` to generate the desired amounts of test
- `runner.py` to run the experiments
- `stats.py` to compute aggregated statistics

Some here scripts can be helpfull if you can run them on a cluster.

# Parameters
You can use `-h` (or `--help`) option to have a list of possible command
parameters.
