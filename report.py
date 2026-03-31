#!/usr/bin/env python3
"""Parse evaluation results and print comparison table."""
import json
import os
import sys
from pathlib import Path


def parse_result(json_path):
    """Extract token metrics from claude --output-format json output."""
    try:
        with open(json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    # Claude CLI JSON output has modelUsage at top level
    usage = {}
    if isinstance(data, dict):
        model_usage = data.get("modelUsage", {})
        # modelUsage is keyed by model name
        for model, metrics in model_usage.items():
            usage["input_tokens"] = metrics.get("inputTokens", 0)
            usage["output_tokens"] = metrics.get("outputTokens", 0)
            usage["cache_creation"] = metrics.get("cacheCreationInputTokens", 0)
            usage["cache_read"] = metrics.get("cacheReadInputTokens", 0)
            usage["cost_usd"] = metrics.get("costUSD", 0)
            break  # Just take first model

        usage["num_turns"] = data.get("numTurns", 0)
        usage["duration_ms"] = data.get("durationMs", 0)
        usage["total_tokens"] = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    return usage if usage else None


def parse_score(score_path):
    """Extract result from verify.sh output. Returns 'PASS' or 'FAIL'."""
    try:
        with open(score_path) as f:
            content = f.read()
        # New format: RESULT: PASS or RESULT: FAIL
        for line in content.strip().split("\n"):
            if line.startswith("RESULT:"):
                return line.split(":")[1].strip()
        # Legacy format: SCORE: X/5
        for line in content.strip().split("\n"):
            if line.startswith("SCORE:"):
                parts = line.split()
                if len(parts) >= 2:
                    score_str = parts[1].split("/")[0]
                    return "PASS" if int(score_str) == 5 else "FAIL"
    except (FileNotFoundError, ValueError):
        pass
    return "FAIL"


def main():
    if len(sys.argv) < 2:
        print("Usage: python report.py <results-dir>")
        sys.exit(1)

    results_dir = Path(sys.argv[1])
    if not results_dir.exists():
        print(f"Results directory not found: {results_dir}")
        sys.exit(1)

    # Collect results across all reps
    results = []
    for rep_dir in sorted(results_dir.glob("rep-*")):
        for json_file in sorted(rep_dir.glob("*.json")):
            name = json_file.stem  # e.g., "A-baseline-3-csv-reporter"
            parts = name.split("-", 2)
            if len(parts) < 2:
                continue

            # Parse config and challenge from filename
            # Format: ConfigName-ChallengeName
            # Find the matching score file
            score_file = rep_dir / f"{name}.score"

            usage = parse_result(json_file)
            score = parse_score(score_file)

            # Try to split config-challenge
            # Filenames are like: A-baseline-1-sqlite-windows
            # We need to figure out config vs challenge
            for config_prefix in ["A-baseline", "B-token-efficient", "C-structured", "D-workflow", "E-hybrid"]:
                if name.startswith(config_prefix):
                    challenge = name[len(config_prefix) + 1:]
                    config = config_prefix
                    break
            else:
                config = parts[0]
                challenge = "-".join(parts[1:])

            results.append({
                "config": config,
                "challenge": challenge,
                "rep": rep_dir.name,
                "score": score,
                "usage": usage or {},
            })

    if not results:
        print("No results found.")
        return

    # Print table
    print("\n## Evaluation Results\n")
    print("| Config | Challenge | Result | Input Tk | Output Tk | Total Tk | Cost |")
    print("|--------|-----------|--------|----------|-----------|----------|------|")

    for r in results:
        u = r["usage"]
        input_tk = u.get("input_tokens", 0)
        output_tk = u.get("output_tokens", 0)
        total_tk = u.get("total_tokens", 0)
        cost = u.get("cost_usd", 0)
        result = r["score"]  # Now "PASS" or "FAIL"

        print(f"| {r['config']:<14} | {r['challenge']:<17} | {result:<6} | {input_tk:>8,} | {output_tk:>9,} | {total_tk:>8,} | ${cost:.3f} |")

    # Summary by config
    print("\n## Summary by Config\n")
    config_stats = {}
    for r in results:
        c = r["config"]
        if c not in config_stats:
            config_stats[c] = {"passes": 0, "total": 0, "tokens": [], "costs": []}
        config_stats[c]["total"] += 1
        if r["score"] == "PASS":
            config_stats[c]["passes"] += 1
        config_stats[c]["tokens"].append(r["usage"].get("total_tokens", 0))
        config_stats[c]["costs"].append(r["usage"].get("cost_usd", 0))

    print("| Config | Pass Rate | Avg Tokens | Avg Cost |")
    print("|--------|-----------|------------|----------|")
    for config in sorted(config_stats.keys()):
        s = config_stats[config]
        pass_rate = f"{s['passes']}/{s['total']}"
        avg_tokens = sum(s["tokens"]) / len(s["tokens"])
        avg_cost = sum(s["costs"]) / len(s["costs"])
        print(f"| {config:<14} | {pass_rate:<9} | {avg_tokens:>10,.0f} | ${avg_cost:.3f}  |")

    # Save report
    report_path = results_dir / "report.md"
    import io
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    print("# Evaluation Report\n")
    print(f"Results directory: {results_dir}\n")
    print("| Config | Challenge | Result | Input Tk | Output Tk | Total Tk | Cost |")
    print("|--------|-----------|--------|----------|-----------|----------|------|")
    for r in results:
        u = r["usage"]
        input_tk = u.get("input_tokens", 0)
        output_tk = u.get("output_tokens", 0)
        total_tk = u.get("total_tokens", 0)
        cost = u.get("cost_usd", 0)
        result = r["score"]
        print(f"| {r['config']:<14} | {r['challenge']:<17} | {result:<6} | {input_tk:>8,} | {output_tk:>9,} | {total_tk:>8,} | ${cost:.3f} |")

    sys.stdout = old_stdout
    with open(report_path, "w") as f:
        f.write(buffer.getvalue())
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
