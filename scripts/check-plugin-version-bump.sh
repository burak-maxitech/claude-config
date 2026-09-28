#!/usr/bin/env bash
# check-plugin-version-bump.sh - fail when the plugin changed but its version did not.
#
# `version` in <plugin>/.claude-plugin/plugin.json is the plugin's update cache key:
# a push that changes the plugin without bumping it reaches no user. /bx:save
# Part 8 enforces the bump inside the skill; this guard covers commits and
# pushes that never went through /bx:save.
#
# Usage: check-plugin-version-bump.sh [base-ref] [head-ref]
#   base-ref  what the plugin is compared against (default: origin/main)
#   head-ref  what is about to be published       (default: HEAD)
#   PLUGIN_DIR env var names the plugin directory (default: bx)
#
# Exit 0 = plugin unchanged, or changed with a different version, or nothing
#          to compare against (unknown base ref: reported, never blocked).
# Exit 1 = plugin changed and the version is the same on both sides, or the
#          manifest is unreadable at head.
# bash 3.2 compatible.

set -uo pipefail

BASE="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"
PLUGIN_DIR="${PLUGIN_DIR:-bx}"
MANIFEST="$PLUGIN_DIR/.claude-plugin/plugin.json"

version_at() {  # <ref> -- the manifest's version at that ref, empty if unreadable
    git show "$1:$MANIFEST" 2>/dev/null \
        | sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
        | head -n 1
}

case "$BASE" in
    *[!0]*) ;;
    *) echo "version-bump guard: no base commit (new branch) - skipped."; exit 0 ;;
esac
if ! git rev-parse --verify --quiet "$BASE^{commit}" > /dev/null; then
    echo "version-bump guard: base ref '$BASE' not found - skipped."
    exit 0
fi
if ! git rev-parse --verify --quiet "$HEAD_REF^{commit}" > /dev/null; then
    echo "version-bump guard: head ref '$HEAD_REF' not found."
    exit 1
fi

if git diff --quiet "$BASE" "$HEAD_REF" -- "$PLUGIN_DIR"; then
    echo "version-bump guard: $PLUGIN_DIR/ unchanged since $BASE."
    exit 0
fi

head_version="$(version_at "$HEAD_REF")"
base_version="$(version_at "$BASE")"

if [ -z "$head_version" ]; then
    echo "version-bump guard: FAILED - cannot read \"version\" from $MANIFEST at $HEAD_REF."
    exit 1
fi
if [ "$head_version" = "$base_version" ]; then
    echo "version-bump guard: FAILED - $PLUGIN_DIR/ changed since $BASE but its version is still $head_version."
    echo "  The version is the update cache key: without a bump no user receives this change."
    echo "  Bump \"version\" in $MANIFEST and add a CHANGELOG.md entry."
    echo "  Changed files:"
    git diff --name-only "$BASE" "$HEAD_REF" -- "$PLUGIN_DIR" | sed 's/^/    /' | head -n 20
    exit 1
fi

echo "version-bump guard: $PLUGIN_DIR/ changed, version ${base_version:-<none>} -> $head_version."
exit 0
