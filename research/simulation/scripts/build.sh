#!/bin/bash
# Compile the unmodified RE87 source into simulation/bin/hurricane.
# Usage: bash simulation/scripts/build.sh
set -euo pipefail
SIM="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$SIM/bin"
gfortran -O2 -march=native -std=legacy -w -o "$SIM/bin/hurricane" "$SIM/model/hurricane.f"
gfortran --version | head -1
ls -la "$SIM/bin/hurricane"
