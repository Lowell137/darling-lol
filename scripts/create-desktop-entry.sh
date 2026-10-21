#!/bin/sh
# Create/update GNOME desktop entry and launcher icon.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo"
python3 scripts/configure.py >/dev/null
python3 build/runtime/tools/desktop-entry.py
