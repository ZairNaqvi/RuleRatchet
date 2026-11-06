#!/usr/bin/env bash
# block.sh "<guard>: <one-line reason>"
# For any hook that blocks an action: call this before exiting so the block is
# counted. Appends a dated BLOCK entry to the repository's log. Never fails the caller.
set -u
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
key=$(printf '%s' "$root" | shasum -a 256 | cut -c1-16)
log="${RULERATCHET_HOME:-$HOME/.ruleratchet}/$key.log"
tool=$(command -v ruleratchet || echo "python3 $(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)/ruleratchet.py")
$tool log "$log" BLOCK "${1:-}" 2>/dev/null
exit 0
