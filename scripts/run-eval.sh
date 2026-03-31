#!/bin/bash
# Run all configs × all challenges in parallel
# Usage: bash scripts/run-eval.sh [--dry-run] [--challenge <name>] [--reps <n>]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

DRY_RUN=""
CHALLENGE_FILTER=""
REPS=1

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN="--dry-run"; shift ;;
        --challenge) CHALLENGE_FILTER="$2"; shift 2 ;;
        --reps) REPS="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Create results directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR="results/${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

echo "=== Evaluation Run ==="
echo "Results: $RESULTS_DIR"
echo "Reps: $REPS"
echo "Dry run: ${DRY_RUN:-no}"
echo ""

# Clean before starting
bash scripts/cleanup.sh

PIDS=()
EXPECTED=0

for rep in $(seq 1 $REPS); do
    for config in configs/*/; do
        for challenge in challenges/*/; do
            CHALLENGE_NAME=$(basename "$challenge")

            # Filter if specified
            if [ -n "$CHALLENGE_FILTER" ] && [ "$CHALLENGE_NAME" != "$CHALLENGE_FILTER" ]; then
                continue
            fi

            CONFIG_NAME=$(basename "$config")
            REP_RESULTS="$RESULTS_DIR/rep-${rep}"
            mkdir -p "$REP_RESULTS"

            echo "Launching: ${CONFIG_NAME} × ${CHALLENGE_NAME} (rep $rep)"
            bash scripts/run-agent.sh "$config" "$challenge" "$REP_RESULTS" $DRY_RUN &
            PIDS+=($!)
            EXPECTED=$((EXPECTED + 1))
        done
    done
done

echo ""
echo "Launched $EXPECTED agents. Waiting for completion..."

# Wait for all background processes
FAILED=0
for pid in "${PIDS[@]}"; do
    if ! wait "$pid"; then
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=== All agents complete ==="
echo "Succeeded: $((EXPECTED - FAILED))/$EXPECTED"
echo "Failed: $FAILED"

# Run report
if command -v python3 &>/dev/null; then
    echo ""
    python3 report.py "$RESULTS_DIR"
fi

echo ""
echo "Results saved to: $RESULTS_DIR"
