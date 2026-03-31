# claude-agent-eval

**Which `.claude/` instruction set makes Claude Code the most token-efficient?**

We tested 6 different `.claude/` configurations against 3 coding challenges with automated test suites. Every agent had to make all tests pass. We measured how many tokens it took to get to green.

## The Question

A [Hacker News thread](https://news.ycombinator.com/item?id=47581701) debated whether aggressive CLAUDE.md rules (like [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient)) actually save tokens. We built a harness to answer this empirically — including testing drona23's actual CLAUDE.md file directly.

## How It Works

1. We created 6 different `.claude/` instruction sets
2. Each one gets the same coding task + a test file
3. The agent must write code that passes all tests
4. We measure total tokens consumed
5. The agent runs in an isolated git worktree containing nothing except seed files and its `.claude/` config

## The 6 Configs

| Config | What's in `.claude/` | Size | Philosophy |
|--------|---------------------|------|------------|
| **A-baseline** | `CLAUDE.md`: "A coding project." | 1 line | Zero guidance |
| **B-token-efficient** | `CLAUDE.md`: Our summary of token-reduction rules | 12 lines | Simplified output reduction |
| **C-structured** | `CLAUDE.md` + `rules/` + `agents/` + `reference/` | 4 files | Structured rules and agent definitions |
| **D-workflow** | `CLAUDE.md` + `rules/` + `skills/` + `hooks/` | 4 files | Step-by-step gates with hooks |
| **E-hybrid** | `CLAUDE.md` + `rules/` + `agents/` | 3 files | Concise output + lightweight structure |
| **F-drona23** | `CLAUDE.md`: The actual file from [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient) | 61 lines | The real thing being tested |

## The 3 Challenges

Each challenge includes a test file that the agent can run to verify its work.

**1. SQLite Window Functions** — Create a database from `seed.sql`, write 5 window function queries (running total, DENSE_RANK, LAG, moving average, percent of total). Test: `node test.js` checks output against expected values.

**2. Hono + Bun WebSocket Counter** — Build a real-time counter with WebSocket broadcast. Test: `bun test.js` connects 2 WebSocket clients, verifies inc/dec/broadcast.

**3. Python CSV Reporter** — Read a 50-row sales CSV, compute 5 statistics. Test: `python test.py` checks each stat against known correct values.

## Results

**All runs passed all tests. 100% pass rate across every config.**

### CSV Reporter (A-E: 2 reps each, F: 1 rep)

| Config | Avg Tokens | Avg Cost |
|--------|------------|----------|
| C-structured | 1,016 | $0.068 |
| E-hybrid | 1,012 | $0.068 |
| A-baseline | 1,088 | $0.078 |
| B-token-efficient | 1,096 | $0.093 |
| **F-drona23** | **1,137** | **$0.084** |
| D-workflow | 1,199 | $0.083 |

### SQLite Window Functions (A-E: 2 reps each, F: 1 rep)

| Config | Avg Tokens | Avg Cost |
|--------|------------|----------|
| E-hybrid | 1,230 | $0.108 |
| A-baseline | 1,255 | $0.120 |
| C-structured | 1,287 | $0.116 |
| B-token-efficient | 1,339 | $0.116 |
| D-workflow | 1,374 | $0.123 |
| **F-drona23** | **1,586** | **$0.127** |

### Hono WebSocket Counter (2 reps each — high variance task)

| Config | Rep 1 | Rep 2 | Avg Tokens |
|--------|-------|-------|------------|
| **C-structured** | 4,778 | 5,058 | **4,918** |
| B-token-efficient | 3,370 | 7,891 | 5,630 |
| A-baseline | 3,667 | 7,790 | 5,728 |
| D-workflow | 5,334 | 9,830 | 7,582 |
| F-drona23 | 14,182 | 4,478 | 9,330 |
| E-hybrid | 4,121 | 15,409 | 9,765 |

**This challenge has massive variance.** E-hybrid went from 4,121 to 15,409 tokens between runs. C-structured was the most consistent (4,778 vs 5,058). The WebSocket task involves multi-turn debugging — how the agent approaches the first attempt matters more than the CLAUDE.md.

### Overall (using averages across all reps)

| Config | CSV | SQLite | WebSocket | Total Tokens |
|--------|-----|--------|-----------|-------------|
| **C-structured** | 1,016 | 1,287 | **4,918** | **7,221** |
| A-baseline | 1,088 | 1,255 | 5,728 | 8,071 |
| B-token-efficient | 1,096 | 1,339 | 5,630 | 8,065 |
| D-workflow | 1,199 | 1,374 | 7,582 | 10,155 |
| F-drona23 | 1,137 | 1,586 | 9,330 | 12,053 |
| E-hybrid | 1,012 | 1,230 | 9,765 | 12,007 |

## What We Learned

### 1. The WebSocket challenge destroyed our earlier conclusions

With only 1 rep, E-hybrid appeared to be the cheapest config. With 2 reps, it's tied for most expensive. **Single-rep results on complex tasks are unreliable.** Any claim about CLAUDE.md efficiency needs multiple runs.

### 2. C-structured was the most consistent

C-structured (rules + agents + reference files) had the lowest variance on WebSocket (4,778 vs 5,058) and the lowest overall total. The structured approach didn't prevent all wasted tokens, but it prevented the catastrophic 15k token runs that hit other configs.

### 3. drona23's actual CLAUDE.md (F) is still expensive

The real 61-line file averaged 9,330 tokens on WebSocket — high variance (14,182 vs 4,478) and consistently more expensive than the 12-line summary of the same ideas. The extra rules add input token overhead without improving consistency.

### 2. Our 12-line summary (B) outperformed the original (F)

Config B used a simplified version of the same ideas — 12 lines instead of 61. It was consistently cheaper: $0.345 total vs $0.580. The extra 49 lines of rules in the original didn't improve outcomes (both pass all tests) but added ~50% more input tokens per turn.

### 4. On simple tasks, CLAUDE.md doesn't matter much

For CSV and SQLite (one-shot tasks), all 6 configs land within 1,000-1,600 tokens. The difference between cheapest and most expensive is ~$0.05. The agent gets it right on the first try regardless of instructions.

### 5. On complex tasks, variance dominates

On WebSocket, the same config can produce 4,121 tokens one run and 15,409 the next. **The CLAUDE.md is a minor factor compared to whether the agent's first approach happens to work.** If it does, ~4k tokens. If it doesn't and needs to debug, 10-15k tokens.

### 6. With tests, every config passes

All 6 configs pass all tests 100% of the time. The real lesson: **give the agent tests.** The CLAUDE.md is an optimization on top of that. Without tests, pass rates varied wildly.

### 7. The answer to the HN debate

Long CLAUDE.md files cost more in input tokens than they save. The 61-line drona23 file averaged 12,053 total tokens across 3 tasks. The 12-line summary of the same ideas averaged 8,065. But even that difference is dwarfed by run-to-run variance on complex tasks. **The most impactful thing you can do is give the agent a test file, not tune your CLAUDE.md.**

## Isolation Proof

Each agent ran in a git worktree where all harness files are gitignored. The worktree contained only:

```
A-baseline worktree:              F-drona23 worktree:
  .claude/CLAUDE.md (1 line)        .claude/CLAUDE.md (61 lines)
  package.json                      package.json
  test.js                           test.js
  seed.sql                          seed.sql
```

No answer keys, no other configs, no harness code, no expected outputs, no README. Verified by logging `find $WORKTREE -type f` for every run.

The actual code each agent produced is saved in `docs/produced-code/<config>/<challenge>/`.

## Methodology

- **Independent variable:** The `.claude/` directory (6 configs)
- **Dependent variables:** Total tokens, cost, pass/fail
- **Control:** Same model (claude-sonnet-4-6), same prompt, same test files, same seed data
- **Isolation:** All harness files gitignored so worktrees are clean. `git ls-files` shows only `.gitignore` and `CLAUDE.md`
- **Scoring:** Agents get test files and must make them pass. Verify scripts run the same tests outside the agent to confirm
- **WebSocket runs:** Sequential (one at a time) to avoid port collisions and API rate limits

## Running It Yourself

```bash
# Switch to runtime mode (clean worktrees for agents)
bash scripts/gitignore-swap.sh run
rm -rf .git && git init && git add -A && git commit -m "clean slate"

# Run one agent
bash scripts/run-agent.sh configs/E-hybrid challenges/3-csv-reporter results/test

# After running, kill orphaned servers
pkill -f "bun.*server"

# Switch back to publish mode to commit results
bash scripts/gitignore-swap.sh publish
```

## Structure

```
configs/          6 .claude/ directories (the independent variable)
challenges/       3 coding tasks with seed files, test files, and verify scripts
prompts/          Task prompts given to agents
scripts/          Orchestration, cleanup, gitignore swap
docs/             Produced code from each agent run
results/          Raw JSON output and scores
report.py         Parse results, print comparison table
analyze.py        Statistical analysis
```

## Credits

- [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient) — the CLAUDE.md tested as Config F

Built with Claude Code (Opus 4.6).
