"""Create one RE87 case directory from the unmodified model inputs.

Usage:
  python make_case.py <case-name> --sounding <file> [--set NAME=VALUE ...]

hurr.in keeps its layout; only the first column of the row whose third column equals NAME changes.
Every override is recorded in case.json so a run can be traced back to its inputs.
"""
import argparse
import json
import shutil
from pathlib import Path

SIM = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--sounding", default=str(SIM / "model" / "s.in"))
    parser.add_argument("--set", action="append", default=[], dest="overrides")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    overrides = dict(item.split("=", 1) for item in args.overrides)
    case_dir = SIM / "runs" / args.case
    case_dir.mkdir(parents=True, exist_ok=True)

    remaining = set(overrides)
    rows = []
    for row in (SIM / "model" / "hurr.in").read_text(encoding="latin-1").splitlines():
        parts = row.split()
        if len(parts) >= 3 and parts[2] in overrides:
            rows.append(row.replace(parts[0], overrides[parts[2]], 1))
            remaining.discard(parts[2])
        else:
            rows.append(row)
    if remaining:
        raise SystemExit(f"unknown hurr.in parameters: {sorted(remaining)}")

    (case_dir / "hurr.in").write_text("\n".join(rows) + "\n", encoding="latin-1", newline="\n")
    shutil.copyfile(args.sounding, case_dir / "s.in")
    (case_dir / "case.json").write_text(
        json.dumps({"case": args.case, "sounding": Path(args.sounding).name, "overrides": overrides, "note": args.note}, indent=2),
        encoding="utf-8",
    )
    print("prepared", args.case, overrides)


if __name__ == "__main__":
    main()
