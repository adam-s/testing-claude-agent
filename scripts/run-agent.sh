#!/bin/bash
# Run a single Claude agent against a challenge with a specific config
# Usage: bash scripts/run-agent.sh <config-dir> <challenge-dir> <results-dir> [--dry-run]
#
# CRITICAL: Worktrees contain ONLY seed files + .claude/ config.
# No answer keys, no other configs, no harness code.
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$PROJECT_DIR/$1"
CHALLENGE_DIR="$PROJECT_DIR/$2"
RESULTS_DIR="$PROJECT_DIR/$3"
DRY_RUN=$4

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: bash scripts/run-agent.sh <config-dir> <challenge-dir> <results-dir> [--dry-run]"
    exit 1
fi

CONFIG_NAME=$(basename "$CONFIG_DIR")
CHALLENGE_NAME=$(basename "$CHALLENGE_DIR")
UUID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo $$)
UUID=${UUID:0:8}

WORKTREE_DIR="/tmp/claude-eval-worktrees/${CONFIG_NAME}-${CHALLENGE_NAME}-${UUID}"
BRANCH_NAME="eval/${CONFIG_NAME}-${CHALLENGE_NAME}-${UUID}"
LOG="/tmp/eval-agent-${CONFIG_NAME}-${CHALLENGE_NAME}.log"
PROMPT_FILE="$PROJECT_DIR/prompts/${CHALLENGE_NAME}.md"

mkdir -p "$RESULTS_DIR"

# APC: bash writes, not the agent
echo "STARTED $(date -u +%Y-%m-%dT%H:%M:%S) ${CONFIG_NAME} ${CHALLENGE_NAME}" > "$LOG"

# Create worktree from local HEAD (contains ONLY .gitignore and CLAUDE.md)
echo "Creating worktree at $WORKTREE_DIR..."
cd "$PROJECT_DIR"
git worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" HEAD 2>/dev/null

# Remove the harness CLAUDE.md — agent gets the CONFIG's CLAUDE.md instead
rm -f "$WORKTREE_DIR/CLAUDE.md"

# Copy config as the worktree's .claude/ directory
echo "Copying config ${CONFIG_NAME}..."
mkdir -p "$WORKTREE_DIR/.claude"
cp -r "$CONFIG_DIR"/* "$WORKTREE_DIR/.claude/" 2>/dev/null || true

# Copy ONLY seed files from challenge (NOT expected/, NOT verify.sh)
echo "Copying seed files..."
if [ -f "$CHALLENGE_DIR/seed-manifest.txt" ]; then
    while IFS= read -r seed_file; do
        seed_file=$(echo "$seed_file" | tr -d '[:space:]')
        [ -z "$seed_file" ] && continue
        mkdir -p "$WORKTREE_DIR/$(dirname "$seed_file")"
        cp "$CHALLENGE_DIR/$seed_file" "$WORKTREE_DIR/$seed_file"
    done < "$CHALLENGE_DIR/seed-manifest.txt"
else
    echo "WARNING: No seed-manifest.txt found for ${CHALLENGE_NAME}"
fi

# VERIFY ISOLATION: Log what the agent can see
echo "=== Worktree contents (agent can see these) ===" >> "$LOG"
find "$WORKTREE_DIR" -type f | grep -v '.git/' | sort >> "$LOG"
echo "=== End worktree contents ===" >> "$LOG"

# Assign unique port for challenges that need a server
# Use PID modulo range to avoid collisions across parallel runs
AGENT_PORT=$((4000 + ($$ % 1000)))
echo "PORT=$AGENT_PORT" >> "$LOG"

# Read the prompt, substitute __PORT__ with unique port
if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: Prompt file not found: $PROMPT_FILE"
    echo "FINISHED 1 $(date -u +%Y-%m-%dT%H:%M:%S)" >> "$LOG"
    exit 1
fi
TASK=$(sed "s/__PORT__/$AGENT_PORT/g" "$PROMPT_FILE")

# Commit seed state in worktree so claude has a clean git state
cd "$WORKTREE_DIR"
git add -A
git commit -m "seed: ${CHALLENGE_NAME} with ${CONFIG_NAME}" --quiet 2>/dev/null || true

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "DRY RUN: Would run claude -p in $WORKTREE_DIR"
    echo '{"result":"dry-run","modelUsage":{}}' > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.json"
    echo "FINISHED 0 $(date -u +%Y-%m-%dT%H:%M:%S)" >> "$LOG"
    exit 0
fi

# Run Claude agent
echo "Running Claude agent (config=${CONFIG_NAME}, challenge=${CHALLENGE_NAME})..."
claude -p "$TASK" \
    --output-format json \
    --dangerously-skip-permissions \
    --max-budget-usd 2.00 \
    --model claude-sonnet-4-6 \
    > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.json" \
    2>"$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.stderr"

EXIT_CODE=$?
echo "Agent finished with exit code $EXIT_CODE"

# Run verify.sh OUTSIDE Claude — copy from main repo, run in worktree
if [ -f "$CHALLENGE_DIR/verify.sh" ]; then
    echo "Running verification..."
    # Copy verify.sh and expected/ into worktree for scoring
    cp "$CHALLENGE_DIR/verify.sh" "$WORKTREE_DIR/"
    if [ -d "$CHALLENGE_DIR/expected" ]; then
        cp -r "$CHALLENGE_DIR/expected" "$WORKTREE_DIR/"
    fi
    cd "$WORKTREE_DIR"
    VERIFY_PORT=$AGENT_PORT bash verify.sh > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.score" 2>&1
    cat "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.score"
else
    echo "No verify.sh found"
    echo "SCORE: 0/5 (no verify.sh)" > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.score"
fi

# Save agent-produced code to docs/produced-code/<config>/<challenge>/
DOCS_DIR="$PROJECT_DIR/docs/produced-code/${CONFIG_NAME}/${CHALLENGE_NAME}"
mkdir -p "$DOCS_DIR"
cd "$WORKTREE_DIR"

# Copy the main code files (not seed files, not test files, not node_modules)
for f in queries.js server.ts report.py index.ts index.js; do
    [ -f "$f" ] && cp "$f" "$DOCS_DIR/"
done

# Save the verify result
grep "RESULT:" "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.score" > "$DOCS_DIR/RESULT.txt" 2>/dev/null || echo "RESULT: UNKNOWN" > "$DOCS_DIR/RESULT.txt"

echo "Code saved to $DOCS_DIR"

# APC: mark finished
echo "FINISHED $EXIT_CODE $(date -u +%Y-%m-%dT%H:%M:%S)" >> "$LOG"

# Clean up worktree
cd "$PROJECT_DIR"
git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
git branch -D "$BRANCH_NAME" 2>/dev/null || true

echo "Done: ${CONFIG_NAME} × ${CHALLENGE_NAME}"
