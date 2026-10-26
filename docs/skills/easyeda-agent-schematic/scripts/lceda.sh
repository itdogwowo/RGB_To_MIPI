#!/usr/bin/env bash
# lceda.sh — thin wrapper around the EasyEDA Pro built-in CLI (lceda-pro / easyeda-pro).
#
# Why: the CLI is the only *authoritative* way for an agent to verify a schematic
# (netlist export + DRC), because it asks the running editor instead of guessing
# geometry from the .esch2 file.
#
# Known state on macOS (2026-10, client 4.1.71):
#   - bundle: /Applications/嘉立创EDA(专业版).app/Contents/MacOS/LCEDA-Pro
#   - `LCEDA-Pro --help` falls through to Node's help, i.e. the CLI entry is NOT
#     reachable by that argument path. The CLI strings do exist inside
#     Contents/Resources/app/app.js, so the feature is present but the launcher
#     entry on macOS still needs to be found (or the app must be started by the
#     user and driven through the bridge).
#   - The GUI must be started by the USER: launching it from an agent sandbox
#     makes the app write ~/Documents/LCEDA-Pro/logs/*.log under the agent's
#     permission context -> "EACCES: permission denied ... LCEDA-Pro/logs".
#
# Usage:
#   tools/lceda.sh probe                 # locate binary + try doctor
#   tools/lceda.sh doctor
#   tools/lceda.sh verify <project.eprj3>  # open headless, run verify payload, close
set -u

BIN_CANDIDATES=(
  "lceda-pro"
  "easyeda-pro"
  "/Applications/嘉立创EDA(专业版).app/Contents/MacOS/LCEDA-Pro"
  "/Applications/EasyEDA Pro.app/Contents/MacOS/EasyEDA-Pro"
)
HERE="$(cd "$(dirname "$0")" && pwd)"

find_bin() {
  for c in "${BIN_CANDIDATES[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
    if [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

json_get() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$(printf '%s' "$1"))" 2>/dev/null; }

cmd="${1:-probe}"
BIN="$(find_bin)" || { echo "no EasyEDA Pro client found"; exit 2; }
echo "client: $BIN"

case "$cmd" in
  probe)
    "$BIN" --help 2>&1 | head -5
    echo "--- doctor ---"
    "$BIN" doctor 2>&1 | head -20
    ;;
  doctor)
    "$BIN" doctor
    ;;
  verify)
    PROJ="${2:?usage: lceda.sh verify <project.eprj3>}"
    OUT="$HERE/../work_lceda"
    mkdir -p "$OUT"
    echo "opening $PROJ"
    SESSION="$("$BIN" open --path "$PROJ" --headless true | json_get "['value']['sessionId']")"
    [ -n "$SESSION" ] || { echo "open failed"; exit 3; }
    echo "session: $SESSION"
    sleep 6
    "$BIN" invoke --session "$SESSION" --ext-uuid eda --timeout 120000 \
        --code "$(cat "$HERE/verify_via_eda.js")" | tee "$OUT/verify.json"
    "$BIN" session close --session "$SESSION" --destroy >/dev/null 2>&1
    echo "evidence: $OUT/verify.json"
    ;;
  *)
    echo "unknown command: $cmd"; exit 1;;
esac
