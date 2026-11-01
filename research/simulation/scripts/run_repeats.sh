#!/bin/bash
# Run the visualization cases first, then the per-condition repeats, seven at a time.
HERE="$(cd "$(dirname "$0")" && pwd)"
RUNS="$HERE/../runs"
bash "$HERE/run_batch.sh" 7 $(tr -d '\r' < "$RUNS/_batch_viz.txt") $(tr -d '\r' < "$RUNS/_batch_repeats.txt")
