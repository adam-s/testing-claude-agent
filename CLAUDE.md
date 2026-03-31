# claude-agent-eval

Deterministic benchmarking for Claude Code instruction sets.

## What this is

A harness that tests 5 different `.claude/` configurations against 3 coding challenges, measures token usage and task completion, and iteratively evolves the configs to find the most token-efficient instruction set.

## Quick commands

- `bash scripts/run-agent.sh configs/A-baseline challenges/3-csv-reporter results/test` — run one agent
- `bash scripts/run-eval.sh` — run all configs × all challenges
- `bash scripts/iterate.sh` — unsupervised evolution loop
- `bash scripts/cleanup.sh` — kill orphans, remove worktrees
- `python report.py results/<dir>/` — print comparison table
- `python analyze.py results/` — statistical analysis

## Structure

- `configs/` — 5 `.claude/` directory configurations (the independent variable)
- `challenges/` — 3 coding tasks with seed files and verify scripts
- `prompts/` — task prompts given to agents
- `scripts/` — orchestration, cleanup, iteration
- `solutions/` — reference implementations (gitignored)
- `results/` — run output (gitignored)
