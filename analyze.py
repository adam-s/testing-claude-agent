#!/usr/bin/env python3
"""Statistical analysis of evaluation results across iterations."""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict


def load_all_results(results_base):
    """Load results from all iteration directories."""
    results_base = Path(results_base)
    all_results = []

    for iter_dir in sorted(results_base.glob("*/")):
        if not iter_dir.is_dir():
            continue
        for rep_dir in sorted(iter_dir.glob("rep-*")):
            for score_file in sorted(rep_dir.glob("*.score")):
                name = score_file.stem
                json_file = rep_dir / f"{name}.json"

                # Parse result (PASS/FAIL)
                passed = False
                try:
                    content = score_file.read_text()
                    for line in content.strip().split("\n"):
                        if line.startswith("RESULT:"):
                            passed = "PASS" in line
                        elif line.startswith("SCORE:"):
                            passed = line.split()[1].startswith("5/")
                except (ValueError, IndexError):
                    pass

                # Parse tokens
                tokens = 0
                cost = 0
                try:
                    data = json.loads(json_file.read_text())
                    for model, metrics in data.get("modelUsage", {}).items():
                        tokens = metrics.get("inputTokens", 0) + metrics.get("outputTokens", 0)
                        cost = metrics.get("costUSD", 0)
                        break
                except:
                    pass

                # Extract config name
                config = "unknown"
                for prefix in ["A-baseline", "B-token-efficient", "C-structured", "D-workflow", "E-hybrid"]:
                    if name.startswith(prefix):
                        config = prefix
                        break

                all_results.append({
                    "iteration": iter_dir.name,
                    "config": config,
                    "passed": passed,
                    "tokens": tokens,
                    "cost": cost,
                })

    return all_results


def analyze(results):
    """Run statistical analysis."""
    # Group by config
    by_config = defaultdict(lambda: {"passes": 0, "total": 0, "tokens": [], "costs": []})
    for r in results:
        c = r["config"]
        by_config[c]["total"] += 1
        if r["passed"]:
            by_config[c]["passes"] += 1
        by_config[c]["tokens"].append(r["tokens"])
        by_config[c]["costs"].append(r["cost"])

    analysis = {"configs": {}, "converged": False, "summary": ""}

    best_efficiency = 0
    best_config = None

    for config, data in sorted(by_config.items()):
        n = data["total"]
        pass_rate = data["passes"] / n if n else 0
        avg_tokens = sum(data["tokens"]) / n if n else 0
        avg_cost = sum(data["costs"]) / n if n else 0

        # Standard deviation of tokens
        if n > 1:
            token_std = (sum((t - avg_tokens) ** 2 for t in data["tokens"]) / (n - 1)) ** 0.5
        else:
            token_std = 0

        # Efficiency: pass rate per 1000 tokens (higher = better)
        efficiency = (pass_rate / avg_tokens * 1000) if avg_tokens > 0 else 0

        analysis["configs"][config] = {
            "n": n,
            "passes": data["passes"],
            "pass_rate": round(pass_rate, 2),
            "avg_tokens": round(avg_tokens, 0),
            "avg_cost": round(avg_cost, 4),
            "efficiency": round(efficiency, 4),
            "token_std": round(token_std, 0),
        }

        if efficiency > best_efficiency:
            best_efficiency = efficiency
            best_config = config

    analysis["best_config"] = best_config
    analysis["summary"] = f"Best: {best_config} (efficiency={best_efficiency:.4f})"

    # Convergence: best config has 100% pass rate and is ahead on efficiency
    if len(results) >= 15 and best_config:
        best_stats = analysis["configs"][best_config]
        if best_stats["pass_rate"] == 1.0:
            analysis["converged"] = True

    return analysis


def main():
    final_mode = "--final" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--final"]

    if not args:
        print("Usage: python analyze.py [--final] <results-dir>")
        sys.exit(1)

    results_dir = args[0]
    results = load_all_results(results_dir)

    if not results:
        print("No results found.")
        # Write empty analysis
        analysis = {"configs": {}, "converged": False, "summary": "No results"}
        latest = sorted(Path(results_dir).glob("*/"))
        if latest:
            with open(latest[-1] / "analysis.json", "w") as f:
                json.dump(analysis, f, indent=2)
        return

    analysis = analyze(results)

    # Save to latest results dir
    latest_dirs = sorted(Path(results_dir).glob("*/"))
    if latest_dirs:
        output_path = latest_dirs[-1] / "analysis.json"
        with open(output_path, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"Analysis saved to: {output_path}")

    # Print summary
    print(f"\n## Analysis Summary\n")
    print(f"Total runs: {len(results)}")
    print(f"Best config: {analysis.get('best_config', 'N/A')}")
    print(f"Converged: {analysis.get('converged', False)}")
    print(f"\n| Config | N | Pass Rate | Avg Tokens | Token Std |")
    print(f"|--------|---|-----------|------------|-----------|")
    for config, stats in sorted(analysis.get("configs", {}).items()):
        print(f"| {config:<14} | {stats['n']} | {stats['passes']}/{stats['n']:<7} | {stats['avg_tokens']:>10,.0f} | {stats['token_std']:>9,.0f} |")


if __name__ == "__main__":
    main()
