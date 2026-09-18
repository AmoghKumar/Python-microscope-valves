#!/usr/bin/env bash
# Merge the shared `main` branch into every task worktree/branch.
#
# Run this (from Git Bash) after committing a shared QoL/bugfix change on
# main, to propagate it into all the per-task branches (Upconcentration
# chemostat, Regular chemostat, Pseudo-Dialysis chemostat, Connection
# chemostat, or any later task branch added the same way). Works from
# anywhere inside the repo or any of its worktrees.
set -euo pipefail

main_branch="main"
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

echo "Fetching latest '$main_branch'..."
git fetch origin "$main_branch" --quiet || true

git worktree list --porcelain | awk '
    /^worktree /{ path = substr($0, 10) }
    /^branch /  { branch = substr($0, 8); sub("refs/heads/", "", branch); print path "\t" branch }
' | while IFS=$'\t' read -r path branch; do
    if [ "$branch" = "$main_branch" ]; then
        continue
    fi
    echo
    echo "── Merging '$main_branch' into '$branch' ($path) ──"
    (
        cd "$path"
        git merge "$main_branch"
    )
done

echo
echo "Done. If any folder above reported a conflict, resolve it there,"
echo "then 'git add' the resolved files and 'git commit' to finish that merge."
