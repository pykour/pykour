# Pykour Benchmarks

## Installation

You will need to install [wrk](https://github.com/wg/wrk) to run the benchmarks.

## Running the benchmarks

To run the benchmarks, simply run the following command:

```bash
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ ./run.sh 8 50
```

You can see the results in the `result.txt` file.
