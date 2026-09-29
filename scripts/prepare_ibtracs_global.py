"""Reduce the downloaded global IBTrACS file to fields used in Cyclone Atlas."""

import csv
import os


SOURCE = "/Users/baeks/Bufs/Codex Files/2026-09-28/ibtracs/ibtracs.since1980.list.v04r01.csv"
OUTPUT = "public/data/ibtracs_global_since1980.csv"
FIELDS = ["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "NATURE", "LAT", "LON", "WMO_WIND", "WMO_PRES"]


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(SOURCE, newline="", encoding="utf-8") as src, open(OUTPUT, "w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=FIELDS)
        writer.writeheader()
        rows = 0
        for row in reader:
            if not row.get("SID", "").strip() or not row.get("SEASON", "").strip():
                continue
            if int(row["SEASON"]) < 1980:
                continue
            writer.writerow({field: row.get(field, "") for field in FIELDS})
            rows += 1
    print(f"Wrote {rows:,} observations to {OUTPUT}")


if __name__ == "__main__":
    main()
