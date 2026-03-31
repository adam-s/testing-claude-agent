# claude-agent-eval: Deterministic benchmarking for Claude Code instruction sets

## Context

We want to **quantify which `.claude/` instruction set produces the most token-efficient agent behavior**, then iterate unsupervised to discover optimal configurations. The independent variable is the **entire `.claude/` directory** — not just CLAUDE.md, but also rules, agents, hooks, skills, and references. The HN discussion around drona23/claude-token-efficient only tested CLAUDE.md prose; we test the full ecosystem.

The iteration loop is borrowed from claudodidact's `/instruction-tuning` skill and intercept2's parallel agent evaluation — but here the variable under test is the `.claude/` instruction set itself.

## Architecture

```
testing-claude-agent/
├── CLAUDE.md                    # Project context ONLY (what's here, how to run)
├── README.md                    # Final report with results (populated at end)
├── .claude/
│   ├── settings.json            # Hooks config (worktree, cleanup, write guards)
│   ├── hooks/
│   │   ├── create-worktree.sh   # Creates /tmp worktrees from local HEAD
│   │   ├── guard-writes.sh      # Prevents agents writing to main repo
│   │   └── cleanup-on-stop.sh   # Kills processes, prunes worktrees
│   └── skills/
│       └── iterate/SKILL.md     # The unsupervised iteration skill
├── configs/                      # Each config is a FULL .claude/ directory
│   ├── A-baseline/              # Minimal — just CLAUDE.md with project name
│   │   └── CLAUDE.md
│   ├── B-token-efficient/       # drona23-style — CLAUDE.md only, aggressive reduction
│   │   └── CLAUDE.md
│   ├── C-structured/            # claudodidact-style — rules, agents, references
│   │   ├── CLAUDE.md
│   │   ├── rules/
│   │   │   └── workflow.md      # MUST/NEVER constraints, verification gates
│   │   ├── agents/
│   │   │   └── builder.md       # Agent definition with budget, tools, protocol
│   │   └── reference/
│   │       └── patterns.md      # Known patterns and anti-patterns
│   ├── D-workflow/              # intercept2-style — skills, hooks, elimination tables
│   │   ├── CLAUDE.md
│   │   ├── rules/
│   │   │   └── build-protocol.md # Step-by-step gates, checklists
│   │   ├── skills/
│   │   │   └── build/SKILL.md   # Multi-step build orchestration
│   │   └── hooks/
│   │       └── verify-before-done.sh  # PreToolUse hook: verify before declaring done
│   └── E-hybrid/               # Best of B+C+D informed by HN counterarguments
│       ├── CLAUDE.md            # Concise but allows reasoning
│       ├── rules/
│       │   └── efficiency.md    # Token-aware constraints
│       └── agents/
│           └── builder.md       # Budget-gated agent
├── challenges/
│   ├── 1-sqlite-windows/
│   │   ├── seed.sql             # 100-row orders table
│   │   ├── package.json         # better-sqlite3
│   │   ├── expected/queries.json # Precomputed correct output
│   │   └── verify.sh            # Automated scoring (0-5)
│   ├── 2-hono-websocket/
│   │   ├── package.json         # hono, bun types
│   │   └── verify.sh            # WS connect + broadcast tests (0-5)
│   └── 3-csv-reporter/
│       ├── data/sales.csv       # 50-row fixture
│       ├── expected/report.txt  # Exact expected output
│       └── verify.sh            # Diff against expected (0-5)
├── docs/
│   └── prompt.md                # The original prompt/conversation that designed this project
├── solutions/                   # .gitignored — reference implementations
├── prompts/                     # Task prompts given to agents
│   ├── challenge-1.md
│   ├── challenge-2.md
│   └── challenge-3.md
├── scripts/
│   ├── run-eval.sh              # Launch 5 parallel agents, collect results
│   ├── run-agent.sh             # Launch one agent in /tmp, capture JSON
│   ├── cleanup.sh               # rm -rf /tmp/eval-*, kill orphans
│   └── iterate.sh              # Unsupervised iteration loop
├── report.py                    # Parse results JSON, print comparison table
├── analyze.py                   # Statistical analysis (Wilcoxon, effect sizes)
├── evolve.py                    # Generate next-gen CLAUDE.md variants
├── results/                     # .gitignored, populated by runs
│   └── <iteration>-<timestamp>/
│       ├── config-a.json
│       ├── config-a.test-results
│       ├── ...
│       └── summary.json
└── .gitignore
```

## Implementation Steps

### Step 1: Initialize the repo
- `git init`, create `.gitignore` (ignore `results/`)
- Create CLAUDE.md for harness development

### Step 2: Create the task suite

Three tiers that directly test the HN hypothesis ("does verbosity help in multi-turn agentic work?"):

#### Challenge 1: SQLite + window functions

**Seed:** Empty directory with `package.json` (better-sqlite3) and `seed.sql` that creates an `orders` table with 100 rows (deterministic data: 10 customers, 10 orders each, fixed dates/amounts).

**Prompt:** *"Create a database from seed.sql. Write queries.js that exports 5 functions, each running a window function query and returning results: (1) running_total — cumulative order amount per customer ordered by date, (2) rank_customers — rank customers by total spend using DENSE_RANK, (3) prev_order — each order with its LAG previous order amount (null for first), (4) moving_avg — 3-order moving average per customer, (5) pct_of_total — each order amount as percentage of customer's total using SUM OVER partition. Run all 5 and print results as JSON."*

**Scoring:** `verify-1.sh` runs `node queries.js`, parses JSON output, compares each of 5 results against `expected/queries.json` (precomputed from seed data). Score 0-5.

**Tricky parts:** SQLite window function syntax (ROWS vs RANGE), LAG with proper default, partition + order-by combos. ~2-3 min for agent.

#### Challenge 2: Hono + Bun WebSocket counter

**Seed:** Empty directory with `package.json` (hono, bun types) and `bunfig.toml`.

**Prompt:** *"Build a Hono server on Bun (port 3456). Serve a single HTML page at / with a counter display and +/- buttons. Use WebSockets: clicking a button sends 'inc' or 'dec', server maintains shared count, broadcasts current count to ALL connected clients as JSON. Counter starts at 0. WebSocket endpoint at /ws."*

**Scoring:** `verify-2.sh`:
1. Start server, wait 1s
2. Connect 2 WebSocket clients via wscat/websocat
3. Client 1 sends `inc` 3 times → both receive `{"count":1}`, `{"count":2}`, `{"count":3}`
4. Client 2 sends `dec` → both receive `{"count":2}`
5. GET / returns HTML containing a `<button>` and a counter element
6. Score 0-5 (server starts, WS connects, inc works, broadcast works, dec works)

**Tricky parts:** Bun's WebSocket upgrade with Hono (not obvious API), broadcasting to all clients, serving static HTML alongside WS.  ~2-3 min for agent.

#### Challenge 3: Python CLI CSV reporter

**Seed:** `data/sales.csv` (50 rows, 5 columns: date, product, region, units, revenue — all deterministic, no edge cases hidden).

**Prompt:** *"Write report.py that reads data/sales.csv and prints: (1) total revenue, (2) top 3 products by units sold, (3) revenue by region sorted descending, (4) month with highest revenue, (5) product with highest average order value. Output as plain text, one section per stat, exact format: 'Total Revenue: $X.XX'. No external dependencies beyond stdlib and csv module."*

**Scoring:** `verify-3.sh` runs `python report.py`, diffs output against `expected/report.txt` (precomputed). Score: 0-5 (one per correct section, exact string match on numbers, flexible on whitespace).

**Tricky parts:** Getting the exact numbers right with float precision, correct sorting, date parsing with stdlib only. ~1-2 min for agent.

### Determinism guarantees

- All seed files checked into repo — identical starting point every run
- All `verify-*.sh` scripts compare against precomputed expected output
- Seed data is fixed (no randomness) — same inputs, same correct answers
- Scoring is binary per check (pass/fail), no subjective grading
- Reference solutions in `solutions/` (gitignored) — verify scripts validated against these first

### Run budget

Each challenge runs 5 times per config (5 configs × 3 challenges × 5 reps = 75 runs).
At ~$0.50-1.00 per run ≈ **$37-75 total** for one full evaluation.
Each run should complete in ~2-5 minutes.

### Step 3: Write the 5 initial `.claude/` config directories

Each config is a complete `.claude/` directory that gets copied into the agent's worktree. The agent sees it as their native `.claude/` environment.

**Config A — Baseline (bare minimum)**
- `CLAUDE.md` only: "A coding project." (1 line)
- No rules, no agents, no hooks, no skills
- Tests: what does Claude do with zero guidance?

**Config B — Token-efficient (drona23-style, CLAUDE.md only)**
- `CLAUDE.md` (~20 lines): No sycophancy, answer line 1, no restatement, no disclaimers, ASCII-only, scope constraints
- No other `.claude/` files — tests whether prose alone moves the needle
- Tests the HN claim: does aggressive output reduction actually save total tokens?

**Config C — Structured rules (claudodidact-style)**
- `CLAUDE.md` (~15 lines): Project context only
- `rules/workflow.md` (~30 lines): MUST/NEVER constraints with rationale, mandatory verification gate before declaring done
- `agents/builder.md` (~25 lines): Agent identity with 50 tool call budget, explicit tool list, step protocol
- `reference/patterns.md` (~20 lines): Known anti-patterns (e.g., "never hardcode paths", "test before committing")
- Tests: do structured rules + agent definitions reduce wasted tokens via guardrails?

**Config D — Workflow gates (intercept2-style)**
- `CLAUDE.md` (~15 lines): Project context only
- `rules/build-protocol.md` (~40 lines): Step-by-step build protocol with gates (read → plan → build → test → verify), elimination checklist, "do not proceed until gate passes"
- `skills/build/SKILL.md` (~30 lines): Multi-step build skill with explicit file outputs per step
- `hooks/verify-before-done.sh`: PreToolUse hook that checks if verify.sh exists and has been run before agent declares done
- Tests: do workflow gates + hooks prevent the retries that waste tokens?

**Config E — Hybrid (best of B+C+D, informed by HN)**
- `CLAUDE.md` (~25 lines): Concise output constraints from B, BUT explicitly allows reasoning tokens ("think before acting, be concise in output")
- `rules/efficiency.md` (~20 lines): Token-aware rules: "prefer editing over rewriting", "read before writing", "no redundant file reads"
- `agents/builder.md` (~15 lines): Lightweight agent with budget gate but no heavy protocol
- Tests: does the middle path (concise + structured but not heavy) win?

### Step 4: Delete `.git` and re-init with clean `.gitignore`
- `rm -rf .git`
- Update `.gitignore` to exclude ALL harness files (configs/, challenges/, prompts/, scripts/, *.py, docs/, solutions/, results/)
- `git init && git add -A && git commit -m "clean slate: only CLAUDE.md and .gitignore tracked"`
- Verify: `git ls-files` shows ONLY `.gitignore` and `CLAUDE.md`
- All harness files exist on disk but are invisible to git worktrees

### Step 5: Write `seed-manifest.txt` for each challenge
Each challenge needs a manifest listing ONLY the files the agent should see:
- `challenges/1-sqlite-windows/seed-manifest.txt`: `seed.sql`, `package.json`
- `challenges/2-hono-websocket/seed-manifest.txt`: `package.json`
- `challenges/3-csv-reporter/seed-manifest.txt`: `data/sales.csv`

NOT listed: `expected/`, `verify.sh` — these stay in the main repo only.

### Step 6: Rewrite `scripts/run-agent.sh`
- Creates a git worktree at `/tmp/claude-eval-worktrees/<name>/` — worktree is CLEAN (only `.gitignore` and harness `CLAUDE.md`)
- Removes the harness `CLAUDE.md` from worktree
- Copies the config's `.claude/` directory in
- Reads `seed-manifest.txt`, copies ONLY listed seed files into worktree
- `git add -A && git commit -m "seed"` in the worktree
- **Verify isolation:** `find $WORKTREE -type f | grep -v .git` must show ONLY seed files + `.claude/`
- Launches Claude CLI, then runs `verify.sh` from main repo AFTER agent completes

### Step 7: Update `scripts/cleanup.sh`
- `rm -rf /tmp/claude-eval-worktrees/`
- `git worktree prune`
- Kill orphaned processes

### Step 9: Write `scripts/run-eval.sh`
- Main orchestrator — launches `run-agent.sh` for each config × challenge as parallel background processes
- Creates timestamped results directory: `results/<iteration>-<timestamp>/`
- Uses `sleep 200 &` + `wait` polling loop (claudodidact pattern) to check `/tmp/eval-agent-*.log` for "done" entries
- Once all agents complete, runs `report.py` then `analyze.py`

### Step 10: Write `report.py`
- Parses each result JSON for token metrics:
  - `inputTokens`, `outputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`
  - `costUSD`, `duration_ms`, `num_turns`
- Reads verify scores (0-5 per challenge)
- Outputs markdown comparison table to stdout AND appends to `results/<dir>/report.md`:
  ```
  | Config     | Challenge | Input Tk | Output Tk | Cost   | Score | Efficiency |
  |------------|-----------|----------|-----------|--------|-------|------------|
  | baseline   | sqlite    | 8,200    | 2,100     | $0.04  | 5/5   | 0.49       |
  | token-eff  | sqlite    | 8,900    | 800       | $0.03  | 4/5   | 0.41       |
  ```
- Efficiency = `score / total_tokens * 1000` (higher = better)

### Step 11: Write `scripts/iterate.sh` — THE UNSUPERVISED LOOP (pure bash, not a Claude agent)

**KEY OPTIMIZATION:** The orchestrator is a bash script, NOT a Claude agent. This eliminates ~100k+ tokens of orchestrator context per iteration. Claude is only invoked for: (a) test agents via `claude -p`, and (b) evolution analysis via `evolve.py` which calls `claude -p` with a targeted prompt.

```bash
#!/bin/bash
MAX_ITERATIONS=10
for i in $(seq 1 $MAX_ITERATIONS); do
  echo "=== Iteration $i ==="

  # 1. Clean
  bash scripts/cleanup.sh

  # 2. Launch all agents (bash manages everything)
  bash scripts/run-eval.sh   # launches claude -p processes in background, polls /tmp logs

  # 3. Report + analyze (python, no Claude)
  RESULTS_DIR=$(ls -td results/*/ | head -1)
  python report.py "$RESULTS_DIR"
  python analyze.py results/

  # 4. Evolve (ONLY step that uses Claude — via claude -p, single prompt)
  #    Uses haiku for 60x cheaper analysis
  python evolve.py "$RESULTS_DIR"

  # 5. Check convergence
  python -c "
import json, sys
r = json.load(open('$RESULTS_DIR/analysis.json'))
if r.get('converged'): sys.exit(0)
sys.exit(1)
  " && echo "Converged at iteration $i" && break

  # 6. Commit
  git add configs/ "$RESULTS_DIR/report.md"
  git commit -m "iteration $i: $(python -c "import json; r=json.load(open('$RESULTS_DIR/analysis.json')); print(r['summary'])")"
done

# Final report
python analyze.py --final results/ > README_RESULTS.md
```

**Convergence:** Stop when champion's efficiency ratio CI overlaps with previous iteration. Max 10 iterations.

### Step 12: Write `evolve.py`
- Uses **`claude -p`** in print mode — single prompt in, single response out, no interactive session, no tool calls
- Runs from the harness repo (not a worktree), so it reads OUR `.claude/` with harness instructions
- Uses `--effort low` and `--max-turns 1` to minimize evolution cost
- Input: `results/<latest>/report.md` + current config directory contents (all files)
- Analysis dimensions — not just CLAUDE.md prose, but the full ecosystem:
  - Did adding a `rules/` file reduce retries?
  - Did an `agents/` definition with a budget gate save tokens?
  - Did a `hooks/` verification step prevent wasted work?
  - Did a `skills/` protocol cause unnecessary overhead?
  - Did a `reference/` file prevent a common mistake?
- Generates 5 new config DIRECTORIES (not just files):
  a. Mutate champion (add/remove/reword one file)
  b. Cross top-2 (merge best files from each)
  c. Structural experiment (e.g., add a hook to the champion, or add a rule to the minimal config)
  d. Wildcard (novel structure Claude suggests)
  e. Champion unchanged (control)
- Generalization rule: changes must work for ANY task, not overfit to these 3 challenges

### Step 13: Write `analyze.py`
- Statistical analysis across all iterations
- Per-config: mean, median, std of tokens and scores
- Between-config: paired Wilcoxon signed-rank, Cohen's d, Bonferroni correction
- Per-challenge breakdown: which config wins on each challenge type?
- Outputs `results/analysis.md` with tables, p-values, verdicts

### Step 14: Write `scripts/cleanup.sh`
- `rm -rf /tmp/claude-eval-worktrees/`
- `rm -f /tmp/eval-agent-*.log`
- `git worktree prune`
- Kill any orphaned claude/node/bun processes

### Step 15: Save the design prompt to `docs/prompt.md`
- Save the full conversation/prompt that designed this project so people can see exactly what was asked
- This is the provenance record — shows how the harness was conceived

### Step 16: Generate README.md with final results
After iterations converge, `analyze.py --final` writes the report into `README.md`:
- Project description and methodology
- Table of all configs tested across all iterations
- Statistical results (which config won, p-values, effect sizes)
- The winning CLAUDE.md config (full text)
- Verdict on the HN debate: does verbosity help or hurt for agentic coding?

## Context Cleanliness (5 Layers of Isolation)

Based on GitHub issues (#39886, #28363, #39981, #38465, #39903) and intercept2's 17 proven cleanup techniques, we implement 5 isolation layers. No single technique is sufficient — all 5 are required.

### Layer 1: Temporal — Fresh sessions per iteration

**Problem:** Subagents inherit parent's system-reminder context containing OLD file contents from deleted/modified rules files (intercept2 "stale context problem").

**Solution:** Each agent runs as a fresh `claude -p` process, not a subagent. No inherited context.

```bash
# In run-agent.sh — each agent is a SEPARATE claude process
claude -p "$TASK" \
  --output-format json \
  --dangerously-skip-permissions \
  --max-budget-usd 2.00 \
  --model claude-sonnet-4-6 \
  --effort low \
  > "$RESULTS_DIR/$CONFIG_NAME.json"
```

**Why `--effort low`:** We're measuring token efficiency of the CLAUDE.md, not the agent's maximum capability. Low effort = fewer tokens per run = cheaper evaluation. All configs get the same effort level (control).

**Why NOT `isolation: "worktree"`:** GitHub issue #39886 — it silently fails, agent runs in main repo with no isolation. We manage our own worktrees via bash.

### Layer 2: Spatial — Worktrees outside repo

**Problem:** Agents modify shared files, worktrees inside repo cause pnpm/workspace confusion.

**Solution:** `scripts/setup-worktree.sh` creates worktrees at `/tmp/claude-eval-worktrees/` via `git worktree add`. Each gets its own branch from LOCAL HEAD (not origin/HEAD).

**Problem:** WorktreeRemove hooks never fire (#28363).

**Solution:** Explicit cleanup in `scripts/cleanup.sh` — never rely on automatic worktree removal.

### Layer 6: Content Isolation — CRITICAL (the answer key problem)

**Problem discovered during Phase 3 testing:** Git worktrees inherit the ENTIRE repo. The agent worktree contains:
- `configs/` — ALL configs including ones not being tested (cross-contamination)
- `challenges/*/expected/` — **THE ANSWER KEY** (expected outputs the agent could read and copy)
- `challenges/*/verify.sh` — the scoring criteria (agent knows exactly what's checked)
- `prompts/` — all prompts for all challenges
- `solutions/` — reference implementations (gitignored but pattern visible)
- `scripts/`, `report.py`, `analyze.py`, `evolve.py` — the entire harness
- The harness `CLAUDE.md` — NOT the config's CLAUDE.md

**Solution:** TWO changes working together:

**Change 1: `.gitignore` everything agents don't need.** Since worktrees branch from HEAD, gitignored files don't appear in worktrees. Add to `.gitignore`:
```
# CRITICAL: Keep these out of agent worktrees
configs/
challenges/
prompts/
scripts/
solutions/
results/
docs/
report.py
analyze.py
evolve.py
handoff.md
*.log
```

This means the repo tracks these files but they're gitignored — wait, that won't work because you can't gitignore already-tracked files.

**Solution: Delete `.git`, update `.gitignore` to exclude everything agents don't need, re-init git.**

Since worktrees branch from HEAD, gitignored files never appear in worktrees. By gitignoring the harness files BEFORE the first commit, they exist on disk but not in git — and therefore not in any worktree.

**Step-by-step:**
1. Delete `.git/` entirely
2. Update `.gitignore` to exclude everything agents don't need:
```
# Harness infrastructure — agents must NEVER see these
configs/
challenges/
prompts/
scripts/
solutions/
results/
docs/
report.py
analyze.py
evolve.py
handoff.md
*.log
node_modules/
__pycache__/
```
3. `git init && git add -A && git commit -m "clean slate"` — only CLAUDE.md and .gitignore get committed
4. Now worktrees from HEAD contain ONLY: `.git`, `.gitignore`, `CLAUDE.md` (the harness CLAUDE.md)

**`run-agent.sh` then:**
1. Creates worktree at `/tmp/claude-eval-worktrees/<name>/`
2. Removes the harness `CLAUDE.md` from worktree
3. Copies the config's `.claude/` directory in (this IS the CLAUDE.md under test)
4. Copies ONLY challenge seed files (from seed-manifest.txt) — NOT `expected/`, NOT `verify.sh`
5. Commits the seed state
6. Agent sees: seed files + `.claude/` — nothing else

**What the agent worktree contains:**
```
<worktree>/
├── .git/                    # Worktree (no harness files visible)
├── .gitignore
├── .claude/                 # The config being tested
│   ├── CLAUDE.md            # The config's CLAUDE.md (NOT the harness one)
│   ├── rules/               # (if config has rules)
│   └── agents/              # (if config has agents)
├── seed.sql                 # Challenge seed file(s) ONLY
└── package.json             # (varies by challenge)
```

**What the agent CANNOT see:**
- Other configs
- Expected outputs (the answer key)
- Verify scripts (the scoring criteria)
- Other challenges
- The harness code
- Solutions or results

**This proves the CLAUDE.md configs are lean and self-contained.** The agent has ONLY the prompt (via `claude -p`) and the `.claude/` directory. Everything else it must figure out from scratch.

**Methodology note for README:** Document that agents operate in clean worktrees with zero harness contamination. The `.gitignore` approach is verifiable — anyone can inspect a worktree with `find $WORKTREE -type f` and confirm only seed + `.claude/` files are present.

### Layer 3: Processual — PID tracking + mandatory cleanup

Before EVERY iteration batch:
```bash
# scripts/cleanup.sh
rm -rf /tmp/claude-eval-worktrees/
rm -f /tmp/eval-agent-*.log
git worktree prune
# Kill orphaned processes from previous runs
pkill -f "node.*queries.js" 2>/dev/null
pkill -f "bun.*server" 2>/dev/null
```

After cleanup, verify clean state:
```bash
WORKTREE_COUNT=$(git worktree list | wc -l)
[ "$WORKTREE_COUNT" -gt 1 ] && echo "ERROR: stale worktrees remain" && exit 1
```

### Layer 4: Informational — Handoff files, not inherited context

**Problem:** Context degrades after 300k tokens (#38465). Memory rules ignored as context fills.

**Solution:** Between iterations, write `handoff.md` (gitignored, ~50 lines):
- Current iteration number + best champion config
- Results table (tokens, scores, efficiency ratios)
- What changed (which configs evolved)
- What's next

New session reads `handoff.md` on startup. Never inherit raw agent output into orchestrator context.

### Layer 5: Verification — Don't trust agent output

**Problem:** Subagents fake thoroughness, inflate counts, report phantom operations (#39981, #39886).

**Solution:** Never score based on what the agent *says* it did. Run `verify.sh` scripts that independently check the worktree's actual output against expected results.

```bash
# In run-agent.sh, AFTER agent completes:
cp "challenges/$CHALLENGE/verify.sh" "$WORKTREE_DIR/"
cd "$WORKTREE_DIR" && bash verify.sh > "$RESULTS_DIR/$CONFIG_NAME-$CHALLENGE.score"
```

## Agent Monitoring (Zero-Token APC)

**CRITICAL DESIGN DECISION:** Agents NEVER write APC logs. The bash wrapper script handles ALL monitoring outside of Claude. This costs zero additional tokens.

### How it works

`run-agent.sh` (a bash script, not a Claude agent) does everything:

```bash
#!/bin/bash
CONFIG=$1; CHALLENGE=$2; RESULTS_DIR=$3
CONFIG_NAME=$(basename "$CONFIG")
CHALLENGE_NAME=$(basename "$CHALLENGE")
LOG="/tmp/eval-agent-${CONFIG_NAME}-${CHALLENGE_NAME}.log"

# Bash writes the log — NOT the agent
echo "STARTED $(date -u +%Y-%m-%dT%H:%M:%S) $CONFIG_NAME $CHALLENGE_NAME" > "$LOG"

claude -p "$(cat prompts/$CHALLENGE_NAME.md)" \
  --output-format json \
  --dangerously-skip-permissions \
  --max-budget-usd 2.00 \
  --model claude-sonnet-4-6 \
  --effort low \
  > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.json" \
  2>"$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.stderr"

EXIT_CODE=$?
echo "FINISHED $EXIT_CODE $(date -u +%Y-%m-%dT%H:%M:%S)" >> "$LOG"

# Run verify.sh OUTSIDE Claude — also zero token cost
cd "$WORKTREE_DIR" && bash verify.sh > "$RESULTS_DIR/${CONFIG_NAME}-${CHALLENGE_NAME}.score" 2>&1
```

The `--output-format json` output already contains all token metrics (inputTokens, outputTokens, cacheTokens, costUSD). No need for the agent to self-report.

### Orchestrator polling

The orchestrator Claude agent uses `sleep 300 &` + Read to poll:

1. **Launch:** Single Bash call starts all agents as background processes
2. **Sleep:** `sleep 300 &` — orchestrator burns near-zero tokens waiting
3. **Read:** Check `/tmp/eval-agent-*.log` for "FINISHED" lines
4. **Repeat** if not all done; proceed to `report.py` when complete

Each polling cycle costs only the tool call overhead (~200 tokens). A full 15-agent eval needs ~3-5 polls.

## Metrics We Track

| Metric | Source | Why |
|--------|--------|-----|
| Input tokens | JSON `--output-format` | CLAUDE.md size affects this directly |
| Output tokens | JSON output | What drona23 claims to reduce |
| Cache tokens | JSON output | Repeated CLAUDE.md content gets cached |
| Total cost | JSON output | The bottom line |
| Tool calls | JSON output | More calls = more input tokens next turn |
| Verify score | `verify.sh` output | Task completion quality (0-5 per challenge) |
| Wall time | JSON output | Latency matters |
| Efficiency ratio | computed | `verify_score / total_tokens * 1000` |

## Statistical Analysis

5 configs x 3 challenges x 5 reps = 75 runs per evaluation round.

### `analyze.py`

**Per-config:** mean, median, std of total tokens and scores. Efficiency ratio with 95% bootstrap CI.

**Between-config:** Paired Wilcoxon signed-rank test, Cohen's d effect size, Bonferroni correction (10 pairs). p < 0.005 after correction = "significant."

**Per-challenge:** Which config wins on each challenge type? This tests whether optimal verbosity depends on task type (the core HN hypothesis).

**Cross-iteration:** Track efficiency ratio trend. Convergence = champion's CI overlaps previous iteration.

**Output:** Markdown tables + CSV + one-line verdict.

## Key Optimizations

1. **Orchestrator is bash, not Claude** — no context window for orchestration
2. **All monitoring/verification in bash** — agents never self-report, verify.sh runs outside Claude
3. **`--effort low`** on all test agents — controlled variable, fewer tokens
4. **`claude -p`** everywhere — single prompt in, single response out, no sessions

## Determinism Notes

- No temperature control in CLI — mitigated by 5 reps + statistical tests
- Specific model ID (`claude-sonnet-4-6`), not alias
- `--effort low` on all agents (same level = controlled variable)
- Randomized run order across reps
- CLAUDE.md input token cost is part of what we measure
- All seed data deterministic (no randomness in fixtures)

## Phased Rollout (test cheap, fix, then spend tokens)

### Phase 0: Build the harness (zero token cost)
- Write all scripts, configs, challenges, seed files, verify scripts, report.py, analyze.py
- Test verify.sh against reference solutions manually (python/node, no Claude)
- Test run-agent.sh in dry-run mode (`echo "mock" > output.json` instead of `claude -p`)
- Test report.py with mock JSON data
- Git commit when harness infrastructure is solid

### Phase 1: Smoke test (1 run, ~$0.50)
- `bash scripts/run-agent.sh configs/A-baseline challenges/3-csv-reporter`
- Verify: JSON output captured? Token metrics present? verify.sh scores correctly?
- Fix any issues. Repeat until one run works end-to-end.

### Phase 2: Small eval (5 runs, ~$2.50)
- 5 configs × 1 challenge × 1 rep
- Verify: all 5 results appear, report.py table renders, configs show differentiation
- Fix parallel execution, cleanup, result collection issues

### Phase 3: Full single eval (15 runs, ~$7.50)
- 5 configs × 3 challenges × 1 rep
- Verify analyze.py runs, identify if any challenge is too easy/hard
- Tune challenge difficulty if needed

### Phase 4: Production runs (75 runs per iteration, ~$37 each)
- Full statistical power (5 reps)
- Run iterate.sh for real evolution cycles

### Phase 5: Report
- Generate README.md with results + methodology
- Save prompt to docs/prompt.md

## README.md Final Report Structure

After iterations converge, `analyze.py --final` generates `README.md`:

### 1. Project Description
What this repo does, why it exists, link to the HN thread

### 2. Methodology
- Independent variable: CLAUDE.md content (5 configs, evolved over N iterations)
- Dependent variables: total tokens, verify score, efficiency ratio
- Control: same model, same effort, same challenges, same seed data
- Sample size: 5 reps per config per challenge per iteration
- Statistical tests: paired Wilcoxon, Cohen's d, Bonferroni correction
- Context cleanliness: 5-layer isolation protocol (temporal, spatial, processual, informational, verification)
- Threats to validity: non-deterministic model output (mitigated by repetitions), cache effects (mitigated by randomized order), CLAUDE.md input token overhead (measured explicitly)

### 3. Challenges
Description of the 3 challenges and their scoring criteria

### 4. Configs Tested
Full text of each CLAUDE.md config with rationale

### 5. Results
Tables: per-config, per-challenge, per-iteration
Statistical significance of differences

### 6. Evolution History
How configs changed across iterations, what phrases helped/hurt

### 7. Verdict
Answer to the HN question: does verbosity help or hurt for agentic coding?
The winning CLAUDE.md config (full text)

### 8. References & Known Issues
Links to all relevant GitHub issues with explanations of how they informed the design:
- anthropics/claude-code#39886 — Worktree isolation silently fails (why we manage our own worktrees)
- anthropics/claude-code#28363 — WorktreeRemove hook never fires (why we explicitly clean up)
- anthropics/claude-code#39981 — Subagent output blindly trusted (why we verify independently)
- anthropics/claude-code#38465 — Context degrades after 300k tokens (why we use fresh sessions)
- anthropics/claude-code#39903 — Subagents billed through API key (cost warning)
- anthropics/claude-code#40339 — Subagent delegation quality (why we use `claude -p` not Agent tool)
- HN thread: https://news.ycombinator.com/item?id=47581701 (the debate that started this)
- drona23/claude-token-efficient (the repo under test)

### 9. Reproduce
`git clone && bash scripts/iterate.sh` — run it yourself

## Housekeeping

### MEMORY.md
Keep MEMORY.md minimal — all project instructions live in `.claude/` files, not memory. MEMORY.md should only contain pointers to user preferences and feedback, not project architecture or implementation details.

### .gitignore
```
results/
solutions/
handoff.md
/tmp/
*.log
```
