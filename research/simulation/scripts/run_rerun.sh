#!/bin/bash
# Rerun the seven cases whose wrapper script was edited while they ran, then the grid sensitivity set.
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/run_batch.sh" 7 t0 er_t0 er_ad_m2_sstfix er_ad_m2_sstup er_ad_p2_sstfix er_ad_p2_sstup ad_m2_sstfix
