#!/usr/bin/env bash
# Mach-O inspection for RiotClientServices. Usage: ./analyze-macho.sh <binary> [outdir]
# Prefers llvm-otool/llvm-objdump (from clang), falls back to otool if present.
set -euo pipefail
BIN="${1:?usage: analyze-macho.sh <mach-o-binary> [outdir]}"
OUT="${2:-logs/macho}"
mkdir -p "$OUT"
OTOOL="$(command -v llvm-otool || command -v otool || true)"
OBJDUMP="$(command -v llvm-objdump || true)"
file "$BIN" | tee "$OUT/file.txt"
[ -n "$OTOOL" ] && { "$OTOOL" -hv "$BIN" > "$OUT/headers.txt" 2>&1; "$OTOOL" -L "$BIN" > "$OUT/linked-libs.txt" 2>&1; echo "wrote headers + linked-libs"; } || echo "no otool/llvm-otool found"
[ -n "$OBJDUMP" ] && "$OBJDUMP" --macho --dylibs-used "$BIN" > "$OUT/dylibs.txt" 2>&1 || true
strings -a "$BIN" | { grep -iE "Metal|MTL|CEF|Chromium|RiotClient|NSApplication|LSOpen|CFBundle" || test "$?" -eq 1; } | sort -u | head -100 | tee "$OUT/strings-of-interest.txt"
echo "done -> $OUT/"
