#!/usr/bin/env bash
# drift report — one line per source file Claude might edit:
# size in bytes, sha256 first-8-chars, and the path. Run at the start of a
# session and paste into chat; Claude diffs against project knowledge and
# refuses to edit any file whose size doesn't match.
set -euo pipefail
cd "$(dirname "$0")"   # always run from the project root, wherever called from

print_file() {
  local p="$1"
  [ -f "$p" ] || return 0            # skip silently if the glob matched nothing
  local bytes hash
  bytes=$(wc -c < "$p" | tr -d ' ')
  hash=$(shasum -a 256 "$p" | cut -c1-8)
  printf "%-40s %8s  %s\n" "$p" "$bytes" "$hash"
}

echo "===== DRIFT REPORT — $(date '+%Y-%m-%d %H:%M:%S') ====="

# Bàrdachd is FLAT — main.py and frontend.py live in the repo root, no
# backend/ subfolder. Flat glob, not backend/*.py. Skip patch scripts
# (bardachd_patch_*.py) — they're tooling, not tracked source.
for f in *.py; do
  case "$f" in bardachd_patch_*.py) continue ;; esac
  print_file "$f"
done                                                     # backend + frontend

# Status / notes docs (tracked because Claude reads them too)
print_file BARDACHD_CLAUDE.md
print_file BARDACHD_TODO.md
print_file BARDACHD_PROJECT_NOTES.md
print_file requirements.txt

# Per-session logs (historical, but tracked so Claude can see the latest)
for f in BARDACHD_SESSION_*.md; do print_file "$f"; done

echo "===== END ====="
