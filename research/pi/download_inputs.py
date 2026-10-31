"""Download the account-free reanalysis inputs for the potential intensity analysis.

Usage: python -I download_inputs.py <empty-output-dir>
Files already complete are skipped, and each one is checked against the server's reported size.
"""
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://downloads.psl.noaa.gov/Datasets"
FILES = {
    "air.mon.mean.nc": f"{BASE}/ncep.reanalysis.derived/pressure/air.mon.mean.nc",
    "shum.mon.mean.nc": f"{BASE}/ncep.reanalysis.derived/pressure/shum.mon.mean.nc",
    "slp.mon.mean.nc": f"{BASE}/ncep.reanalysis.derived/surface/slp.mon.mean.nc",
    "sst.mnmean.nc": f"{BASE}/noaa.ersst.v5/sst.mnmean.nc",
}
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

for name, url in FILES.items():
    target = out / name
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as head:
        size = int(head.headers["Content-Length"])
    if target.exists() and target.stat().st_size == size:
        print("skip", name, flush=True)
        continue
    start = time.time()
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as f:
        while chunk := response.read(1 << 20):
            f.write(chunk)
    if partial.stat().st_size != size:
        raise SystemExit(f"{name}: expected {size} bytes, got {partial.stat().st_size}")
    partial.replace(target)
    print(f"done {name} {size / 1e6:.1f} MB in {time.time() - start:.0f}s", flush=True)
    time.sleep(5)
print("all files complete", flush=True)
