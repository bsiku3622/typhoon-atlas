#!/bin/bash
# Double-resolution runs. The source copy differs from the original in M, N and the TVRDIF array size,
# which is fixed at 100 levels in subroutine CAPE and overflows at N=160.
HERE="$(cd "$(dirname "$0")" && pwd)"
SIM="$(cd "$HERE/.." && pwd)"
sed -i -E 's/TVRDIF\(100\)/TVRDIF(400)/' "$SIM/model_grid/hurricane_fine.f"
gfortran -O2 -march=native -std=legacy -w -o "$SIM/bin/hurricane_fine" "$SIM/model_grid/hurricane_fine.f"
HURRICANE_BIN="$SIM/bin/hurricane_fine" bash "$HERE/run_batch.sh" 4 g_fine_t0 g_fine_ad_m2_sstfix g_fine_ad_p2_sstfix g_fine_ad_p2_sstup
