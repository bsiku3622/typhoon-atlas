#!/bin/bash
# Run several prepared cases in parallel. Each case is single-threaded.
# Usage: bash simulation/scripts/run_batch.sh <jobs> <case> [<case> ...]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
JOBS="$1"; shift
printf '%s\n' "$@" | xargs -P "$JOBS" -I{} bash "$HERE/run_case.sh" {}
status=$?
for c in "$@"; do
  meta="$HERE/../runs/$c/run_meta.txt"
  if [ -f "$meta" ]; then echo "$c: $(grep -E 'exit_code|wall_seconds' "$meta" | tr '\n' ' ')"; else echo "$c: no meta"; fi
done
exit "$status"
