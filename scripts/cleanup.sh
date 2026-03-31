#!/bin/bash
# Clean up all evaluation artifacts
set -e

echo "Cleaning up..."

# Remove worktrees
rm -rf /tmp/claude-eval-worktrees/
git worktree prune 2>/dev/null || true

# Remove APC logs
rm -f /tmp/eval-agent-*.log

# Kill orphaned processes from previous runs
pkill -f "node.*queries.js" 2>/dev/null || true
pkill -f "bun.*server" 2>/dev/null || true

# Verify clean state
WORKTREE_COUNT=$(git worktree list 2>/dev/null | wc -l)
if [ "$WORKTREE_COUNT" -gt 1 ]; then
    echo "WARNING: $((WORKTREE_COUNT - 1)) stale worktrees remain"
    git worktree list
else
    echo "Clean: no stale worktrees"
fi

echo "Cleanup complete"
