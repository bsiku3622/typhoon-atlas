#!/bin/bash
# Run every case listed in runs/_batch_main.txt, seven at a time.
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/run_batch.sh" 7 $(tr -d '\r' < "$HERE/../runs/_batch_main.txt")
