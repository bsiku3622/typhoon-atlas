#!/bin/bash
# Run one RE87 case from an existing case directory holding hurr.in and s.in.
# Usage: bash simulation/scripts/run_case.sh <case-name>
# Output goes to simulation/runs/<case-name>/output. Wall-clock time is stored in run_meta.txt.
set -uo pipefail
SIM="$(cd "$(dirname "$0")/.." && pwd)"
CASE_DIR="$SIM/runs/$1"
cd "$CASE_DIR" || exit 2
[ -f hurr.in ] && [ -f s.in ] || { echo "missing inputs in $CASE_DIR"; exit 2; }
rm -rf output
mkdir -p output
start=$(date +%s)
BIN="${HURRICANE_BIN:-$SIM/bin/hurricane}"
nice -n 10 "$BIN" > stdout.txt 2> stderr.txt
code=$?
end=$(date +%s)
{
  echo "case=$1"
  echo "exit_code=$code"
  echo "wall_seconds=$((end - start))"
  echo "finished=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "binary=$(basename "$BIN")"
  echo "sha256_binary=$(sha256sum "$BIN" | cut -d' ' -f1)"
} > run_meta.txt
exit "$code"
