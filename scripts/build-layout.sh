#!/usr/bin/env bash
# Build an SSMS 22 offline layout under Wine.
# Requires: wine, wine-mono, winetricks, and a network connection.
set -euo pipefail

LAYOUT="${1:-$HOME/Downloads/smss/SSMS_Layout}"
BOOTSTRAP="${BOOTSTRAP:-vs_SSMS.exe}"
# Base SSMS + offline help. Add IS/RS here if you deploy those.
ADD=(--add Microsoft.Component.HelpViewer)
# ADD+=(--add Microsoft.SSMS.Component.IS --add Microsoft.SSMS.Component.RS)

command -v wine >/dev/null || { echo "wine not found"; exit 1; }
[ -f "$BOOTSTRAP" ] || { echo "missing $BOOTSTRAP (download the online bootstrapper)"; exit 1; }

# Map a Linux dir to a path INSIDE the C: drive. The VS bootstrapper
# rejects drive letters that look like network shares (e.g. Z:), so we
# build inside the prefix and move the result afterwards.
WIN="$(wine winepath -w "$LAYOUT" 2>/dev/null || true)"
case "$WIN" in
  'Z:'*|'') echo "unusable Windows path: '$WIN'"; exit 1;;
esac
mkdir -p "$LAYOUT"

export WINEDEBUG=-all
echo "Building layout -> $WIN"
wine "$BOOTSTRAP" --layout "$WIN" "${ADD[@]}" --passive
rc=$?

echo
echo "exit=$rc"
echo "Verify with: scripts/verify-layout.py '$LAYOUT'"
echo "Then move to the FINAL path before installing on Windows."
