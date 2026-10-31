"""Download NCEP/DOE Reanalysis 2 monthly fields for the reanalysis sensitivity check.

Usage: python -I download_r2.py <empty-output-dir>
The PSL server can stall, so every file is retried and checked against its reported size.
"""
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2.derived"
FILES = {
    "air.mon.mean.nc": f"{BASE}/pressure/air.mon.mean.nc",
    "rhum.mon.mean.nc": f"{BASE}/pressure/rhum.mon.mean.nc",
    "mslp.mon.mean.nc": f"{BASE}/surface/mslp.mon.mean.nc",
}
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

for name, url in FILES.items():
    target = out / name
    for attempt in range(1, 7):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                size = int(response.headers["Content-Length"])
                if target.exists() and target.stat().st_size == size:
                    print("skip", name, flush=True)
                    break
                partial = target.with_suffix(target.suffix + ".part")
                with partial.open("wb") as f:
                    while chunk := response.read(1 << 20):
                        f.write(chunk)
            if partial.stat().st_size != size:
                raise OSError(f"size {partial.stat().st_size} != {size}")
            partial.replace(target)
            print(f"done {name} {size / 1e6:.1f} MB (attempt {attempt})", flush=True)
            break
        except Exception as error:  # A stalled or dropped connection is retried with a longer pause.
            print(f"retry {name} attempt {attempt}: {error}", flush=True)
            time.sleep(30 * attempt)
    else:
        raise SystemExit(f"failed: {name}")
    time.sleep(5)
print("all files complete", flush=True)
