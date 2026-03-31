#!/bin/bash
# Unsupervised iteration loop — pure bash orchestrator
# Usage: bash scripts/iterate.sh [--max-iterations N] [--reps N]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

MAX_ITERATIONS=10
REPS=5

while [ $# -gt 0 ]; do
    case "$1" in
        --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
        --reps) REPS="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo "=== Iteration Loop ==="
echo "Max iterations: $MAX_ITERATIONS"
echo "Reps per eval: $REPS"
echo ""

for i in $(seq 1 $MAX_ITERATIONS); do
    echo "=========================================="
    echo "=== Iteration $i of $MAX_ITERATIONS ==="
    echo "=========================================="

    # 1. Clean
    bash scripts/cleanup.sh

    # 2. Run full eval
    bash scripts/run-eval.sh --reps "$REPS"

    # 3. Report + analyze (python, no Claude)
    RESULTS_DIR=$(ls -td results/*/ 2>/dev/null | head -1)
    if [ -z "$RESULTS_DIR" ]; then
        echo "ERROR: No results directory found"
        exit 1
    fi

    python3 report.py "$RESULTS_DIR"
    python3 analyze.py results/

    # 4. Evolve (calls claude -p with targeted prompt)
    python3 evolve.py "$RESULTS_DIR"

    # 5. Check convergence
    if python3 -c "
import json, sys
try:
    r = json.load(open('${RESULTS_DIR}/analysis.json'))
    if r.get('converged'): sys.exit(0)
except: pass
sys.exit(1)
" 2>/dev/null; then
        echo "=== Converged at iteration $i ==="
        break
    fi

    # 6. Commit
    git add configs/ "${RESULTS_DIR}/report.md" 2>/dev/null || true
    SUMMARY=$(python3 -c "
import json
try:
    r = json.load(open('${RESULTS_DIR}/analysis.json'))
    print(r.get('summary', 'iteration $i'))
except:
    print('iteration $i')
" 2>/dev/null)
    git commit -m "iteration $i: $SUMMARY" --quiet 2>/dev/null || true

    echo ""
done

# Final report
echo "=== Generating Final Report ==="
python3 analyze.py --final results/
echo "Done. See README_RESULTS.md"
