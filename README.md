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

# Example

## Generating tests
```bash
#./generator.py 100 -l ./lopstr-2024/data -g ./lopstr-2024/utils.py
```
This command was previously run to generate the test files (here is why it is
commented). It generates:
- 100 .dzn files
- stores them inside *./lopstr-2024/data* folder  (using -l flag)
- uses the generator function in *./lopstr-2024/utils.py*

## Running tests
You can run the test on your machine using the following command:
```bash
./runner.py ./lopstr-2024/freeda-model.mzn ./lopstr-2024/data/ -l lopstr-2024/my-results.json --solvers gurobi gecode chuffed cpsatlp #the last one is ortools
```
It uses the following arguments:
- *./lopstr-2024/freeda-model.mzn* the path to the model
- *./lopstr-2024/data/* path to the previously generated data files
- lopstr-2024/data/my-results.json (-l flag) the name of the result files
- the solvers (--solvers flag)

## Calculate statistics
```bash
./stats.py lopstr-2024/my-results.json
```
The argument is the location to the previously generated result json file.