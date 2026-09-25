#!/usr/bin/env bash
# Runs the full experiment campaign in the background (resumable) and then the figures.
cd "$(dirname "$0")/.." || exit 1
mkdir -p results
nohup python3 -m sim.experiments --procs "${PROCS:-4}" --exp ${EXPS:-ccdf peak burst power segments dmax users tau V hetero rician mismatch traffic} > results/run_all.log 2>&1 &
echo "launched, log: results/run_all.log"
