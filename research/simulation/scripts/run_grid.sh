#!/bin/bash
# Grid sensitivity: the same four experiments at half and at double resolution.
# Usage: bash simulation/scripts/run_grid.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
SIM="$HERE/.."
for v in coarse fine; do
  gfortran -O2 -march=native -std=legacy -w -o "$SIM/bin/hurricane_$v" "$SIM/model_grid/hurricane_$v.f"
done
HURRICANE_BIN="$(cd "$SIM/bin" && pwd)/hurricane_coarse" bash "$HERE/run_batch.sh" 4 g_coarse_t0 g_coarse_ad_m2_sstfix g_coarse_ad_p2_sstfix g_coarse_ad_p2_sstup
HURRICANE_BIN="$(cd "$SIM/bin" && pwd)/hurricane_fine" bash "$HERE/run_batch.sh" 4 g_fine_t0 g_fine_ad_m2_sstfix g_fine_ad_p2_sstfix g_fine_ad_p2_sstup
