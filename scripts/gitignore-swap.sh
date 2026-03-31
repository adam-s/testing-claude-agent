#!/bin/bash
# Swap between runtime and publish .gitignore modes.
#
# Runtime mode:  Agent worktrees contain ONLY .gitignore + CLAUDE.md (clean isolation)
# Publish mode:  All harness files tracked for committing to GitHub
#
# Usage:
#   bash scripts/gitignore-swap.sh run      # before running agents
#   bash scripts/gitignore-swap.sh publish  # before committing to GitHub
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODE=$1

case "$MODE" in
    run)
        cp .gitignore.run .gitignore
        echo "Switched to RUNTIME mode — agent worktrees will be clean"
        echo "Tracked files: $(git ls-files 2>/dev/null | wc -l | tr -d ' ')"
        ;;
    publish)
        cp .gitignore.publish .gitignore
        echo "Switched to PUBLISH mode — all harness files will be tracked"
        echo "Run 'git add -A' to stage everything"
        ;;
    *)
        echo "Usage: bash scripts/gitignore-swap.sh [run|publish]"
        echo ""
        echo "  run      Clean worktrees for agent evaluation (default for testing)"
        echo "  publish  Track all files for committing to GitHub"
        exit 1
        ;;
esac
