#!/bin/bash
# When running coverage, a simple coverage run will only give the main thread of the main process.
# If we set the COVERAGE_PROCESS_START environemnt variable, we can trigger coverage 
# in each subprocess, then combine everything.
# This will process the coverage run and combine all the separate processes report
# It cannot be done by VS Code automatically apparently.
#
# You need a .coveragerc file with:
# [run]
# branch = True
# parallel = True
# concurrency = multiprocessing

# If you want to run it for a single process, do this (for exemple):
# export COVERAGE_PROCESS_START=.coveragerc; coverage run test_mainProcess.py; coverage combine; coverage html; open htmlcov/index.html

# Step 1: clean old results
rm -rf .coverage.* htmlcov

# Step 2: export environment variable
export COVERAGE_PROCESS_START=.coveragerc

# Step 3: run tests via unittest (or pytest)
python -m coverage run -m unittest discover -s tests

# Step 4: check subprocess reports were generated
ls .coverage*

# Step 5: combine reports and generate HTML
python -m coverage combine
python -m coverage html
open htmlcov/index.html  # macOS only