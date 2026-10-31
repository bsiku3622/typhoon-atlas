"""Compare candidate environmental predictors of simulated intensity across the experiments.

Usage: python -I mechanism_test.py <simulation-dir> <output-csv>
All predictors are computed from the initial sounding, so they carry no feedback from the storm:
  init_dk   surface saturation MSE minus lowest-level MSE
  cape_sat  CAPE of a parcel saturated at SST and surface pressure against the environment
  sst       sea surface temperature
  vmaxth    the model's own potential intensity
Experiments run with the moist-adiabatic design at standard physics. T-1 and T-2 with SST fixed are shown
but flagged because they do not reach a steady state; peak intensity is the fairer target for them.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tcpyPI import cape

sim = Path(sys.argv[1])
sys.path.insert(0, str(sim / "scripts"))
import soundings as sd  # noqa: E402

out = Path(sys.argv[2])
results = sim / "results"
run = pd.read_csv(results / "run_summary.csv").set_index("case")
init = pd.read_csv(results / "initial_disequilibrium.csv").set_index("case")
cases = [f"{p}_{d}_{s}" for p, s in (("ad", "sstfix"), ("ad", "sstup"), ("q", "sstfix")) for d in ("m2", "m1", "p1", "p2")] + ["t0"]
rows = []
for case in cases:
    s = sd.read(sim / "runs" / case / "s.in")
    keep = s.p >= 50
    e = float(sd.es(np.array(s.sst)))
    rs = 0.622 * e / (1013.0 - e)
    value, _, _, _ = cape(s.sst + 273.15, rs, 1013.0, s.t[keep] + 273.15, s.r[keep] / 1000.0, s.p[keep], ascent_flag=0, ptop=50, miss_handle=1)
    rows.append({"case": case, "sst": s.sst, "init_dk": init.loc[case, "init_dk_kj"], "cape_sat": float(value), "vmaxth": run.loc[case, "vmaxth"],
                 "v_mean": run.loc[case, "v_mean_d8_15"], "v_peak": run.loc[case, "v_peak_24h"], "steady": not (case in ("ad_m2_sstfix", "ad_m1_sstfix", "q_m2_sstfix", "q_m1_sstfix"))})
table = pd.DataFrame(rows).set_index("case")
members = ["t0", "t0_n1", "t0_n2", "t0_n3", "t0_n4"]
table.loc["t0", "v_mean"] = run.loc[members, "v_mean_d8_15"].mean()
table.loc["t0", "v_peak"] = run.loc[members, "v_peak_24h"].mean()
table.to_csv(out)
pd.set_option("display.width", 180, "display.float_format", lambda v: f"{v:.2f}")
print(table.to_string())


def report(frame, target, label):
    print(f"-- {label}: n={len(frame)}, target {target}")
    for predictor in ("init_dk", "cape_sat", "sst"):
        r = np.corrcoef(frame[predictor], frame[target])[0, 1]
        fit = np.polyfit(frame[predictor], frame[target], 1)
        rmse = np.sqrt(np.mean((np.polyval(fit, frame[predictor]) - frame[target]) ** 2))
        print(f"   {predictor:9s} r={r:+.3f}  r2={r * r:.3f}  rmse={rmse:.2f} m/s")
    usable = frame[frame.index != "q_p2_sstfix"]
    r = np.corrcoef(usable["vmaxth"], usable[target])[0, 1]
    print(f"   vmaxth    r={r:+.3f}  r2={r * r:.3f}  (without q_p2_sstfix, n={len(usable)})")


report(table, "v_peak", "all moist-adiabatic runs")
report(table[table.steady], "v_mean", "runs that reach a steady state")
warm = table.loc[["t0", "ad_p1_sstfix", "ad_p2_sstfix", "q_p1_sstfix", "q_p2_sstfix"]]
report(warm, "v_mean", "warming with SST fixed, both humidity treatments")
