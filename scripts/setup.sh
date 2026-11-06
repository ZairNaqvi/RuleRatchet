#!/usr/bin/env bash
# Installs this repository's git hooks into this clone only.
# Never sets core.hooksPath; other repositories on the machine are untouched.
set -eu
root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "setup.sh: run inside the repository" >&2; exit 1; }
cd "$root"
[ -d scripts/hooks ] || { echo "setup.sh: scripts/hooks missing; run from the repository root" >&2; exit 1; }
hookdir=$(git rev-parse --git-path hooks)
mkdir -p "$hookdir"
for hook in scripts/hooks/*; do
  name=$(basename "$hook")
  case "$name" in *.sh|*.event) continue ;; esac
  cp "$hook" "$hookdir/$name"
  chmod +x "$hookdir/$name"
  echo "installed $name"
done
