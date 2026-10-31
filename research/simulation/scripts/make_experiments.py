"""Generate soundings and case directories for the temperature experiments.

Usage: python make_experiments.py [--base-only]

Base state n28: the construction of the bundled neutral s.in (24.89 C SST) rebuilt for a 28 C sea, with
the same sea-air temperature gap and RH profile. Physics are the package's standard values, including
TMIN=133 K, the value the guide describes as never invoked; the shipped first column has TMIN=210 K.

Designs for dT in -2, -1, +1, +2 K:
  ad_*_sstfix  boundary layer warmed by dT and re-lifted along a pseudo-adiabat, RH preserved, SST fixed
  ad_*_sstup   same atmosphere with SST raised by dT
  q_*_sstfix   same temperature as ad, mixing ratio preserved and capped at saturation, SST fixed
  un_*_sst*    uniform shift, RH preserved, SST fixed or raised, dT = +/-2 only, for the vertical shape
T0 repeats with tiny boundary-layer offsets measure internal variability.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import neutral as nt  # noqa: E402
import soundings as sd  # noqa: E402

SIM = HERE.parent
STORE = SIM / "runs" / "_soundings"
STORE.mkdir(parents=True, exist_ok=True)
COMMON = ["--set", "TMIN=133.0", "--set", "TIMEPL=0.0416667"]
SST0 = 28.0

template = sd.read(SIM / "model" / "s.in")
n28 = nt.neutral_state(template, SST0 - template.sst, SST0)
sd.write(n28, STORE / "n28.in")


def tag(dt):
    return ("p" if dt > 0 else "m") + str(abs(dt))


def prepare(name, snd, note, extra=()):
    path = STORE / f"{name}.in"
    sd.write(snd, path)
    subprocess.run(
        [sys.executable, str(HERE / "make_case.py"), name, "--sounding", str(path), "--note", note, *COMMON, *extra],
        check=True, stdout=subprocess.DEVNULL,
    )
    return name


if "--base-only" in sys.argv:
    print(prepare("t0", n28, "Base state: neutral sounding rebuilt for SST 28 C"))
    print(prepare("t0_tmin210", n28, "Base state with the shipped TMIN", ["--set", "TMIN=210.0"]))
    print(prepare("s_tmin133", template, "Bundled s.in with the guide's TMIN"))
    print(prepare("er_tmin133", template, "Emanuel and Rotunno 2011 settings with the guide's TMIN",
                  ["--set", "XHL=1000.0", "--set", "XVL=1000.0", "--set", "DISS=0.0", "--set", "PDEP=n"]))
    raise SystemExit

ER = ["--set", "XHL=1000.0", "--set", "XVL=1000.0", "--set", "DISS=0.0", "--set", "PDEP=n"]
cases = [prepare("t0", n28, "Base state: neutral sounding rebuilt for SST 28 C")]
cases.append(prepare("er_t0", n28, "Base state, large mixing lengths without dissipative heating", ER))
for dt in (-2, 2):
    warm = nt.neutral_state(n28, dt, SST0)
    cases.append(prepare(f"er_ad_{tag(dt)}_sstfix", warm, f"Large-mixing physics, moist-adiabatic dT={dt}, SST fixed", ER))
    cases.append(prepare(f"er_ad_{tag(dt)}_sstup", sd.replace(warm, sst=SST0 + dt), f"Large-mixing physics, moist-adiabatic dT={dt}, SST raised", ER))
for dt in (-2, -1, 1, 2):
    warm = nt.neutral_state(n28, dt, SST0)
    cases.append(prepare(f"ad_{tag(dt)}_sstfix", warm, f"Moist-adiabatic dT={dt}, RH preserved, SST fixed"))
    cases.append(prepare(f"ad_{tag(dt)}_sstup", sd.replace(warm, sst=SST0 + dt), f"Moist-adiabatic dT={dt}, RH preserved, SST raised"))
    cases.append(prepare(f"q_{tag(dt)}_sstfix", nt.neutral_state(n28, dt, SST0, "q"), f"Moist-adiabatic dT={dt}, mixing ratio preserved, SST fixed"))
    if abs(dt) == 2:
        uni = sd.uniform_shift(n28, dt, "rh")
        cases.append(prepare(f"un_{tag(dt)}_sstfix", uni, f"Uniform dT={dt}, RH preserved, SST fixed"))
        cases.append(prepare(f"un_{tag(dt)}_sstup", sd.replace(uni, sst=SST0 + dt), f"Uniform dT={dt}, RH preserved, SST raised"))
for i, offset in enumerate((-0.02, -0.01, 0.01, 0.02), start=1):
    cases.append(prepare(f"t0_n{i}", nt.neutral_state(n28, offset, SST0), f"Noise member: boundary layer offset {offset} K"))

(SIM / "runs" / "_experiment_cases.json").write_text(json.dumps(cases, indent=1), encoding="utf-8")
print(len(cases), "cases prepared")
print(" ".join(cases))
