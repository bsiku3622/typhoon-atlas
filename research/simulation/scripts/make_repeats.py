"""Prepare per-condition repeat runs and dense-output runs for visualization.

Usage: python make_repeats.py
Repeats use the same tiny boundary-layer offsets as the T0 repeats, so each condition has five members
and condition-by-condition noise can be measured instead of assuming the T0 value.
Visualization runs are the original cases with one-day output replaced by six-hourly means. Output
frequency must not change the physics, which is checked by comparing time.out with the original run.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import neutral as nt  # noqa: E402
import soundings as sd  # noqa: E402

SIM = HERE.parent
STORE = SIM / "runs" / "_soundings"
COMMON = ["--set", "TMIN=133.0", "--set", "TIMEPL=0.0416667"]
OFFSETS = (-0.02, -0.01, 0.01, 0.02)
SST0 = 28.0

template = sd.read(SIM / "model" / "s.in")
n28 = nt.neutral_state(template, SST0 - template.sst, SST0)


def prepare(name, snd, note, extra=()):
    path = STORE / f"{name}.in"
    sd.write(snd, path)
    subprocess.run(
        [sys.executable, str(HERE / "make_case.py"), name, "--sounding", str(path), "--note", note, *COMMON, *extra],
        check=True, stdout=subprocess.DEVNULL,
    )
    return name


viz = []
for case in ("t0", "ad_p2_sstup", "ad_m2_sstup", "ad_p2_sstfix", "ad_m2_sstfix"):
    source = STORE / f"{case}.in"
    name = f"v_{case}"
    viz.append(prepare(name, sd.read(source), f"Dense output of {case}", ["--set", "PLTIME=0.25", "--set", "TAVE=0.25"]))

repeats = []
conditions = (
    ("ad_m2_sstup", -2, SST0 - 2, "rh"), ("ad_m1_sstup", -1, SST0 - 1, "rh"), ("ad_p1_sstup", 1, SST0 + 1, "rh"), ("ad_p2_sstup", 2, SST0 + 2, "rh"),
    ("ad_p1_sstfix", 1, SST0, "rh"), ("ad_p2_sstfix", 2, SST0, "rh"), ("q_p1_sstfix", 1, SST0, "q"), ("q_p2_sstfix", 2, SST0, "q"),
)
for base, dt, sst, humidity in conditions:
    for i, offset in enumerate(OFFSETS, start=1):
        snd = nt.neutral_state(n28, dt + offset, SST0, humidity)
        repeats.append(prepare(f"{base}_n{i}", sd.replace(snd, sst=sst), f"Repeat of {base}: boundary layer offset {offset} K"))

(SIM / "runs" / "_batch_viz.txt").write_text(" ".join(viz) + "\n", encoding="utf-8", newline="\n")
(SIM / "runs" / "_batch_repeats.txt").write_text(" ".join(repeats) + "\n", encoding="utf-8", newline="\n")
print(len(viz), "visualization cases,", len(repeats), "repeat cases")
