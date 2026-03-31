#!/usr/bin/env python3
"""Evolve configs based on evaluation results. Uses claude -p for analysis."""
import json
import os
import subprocess
import sys
from pathlib import Path


def read_config(config_dir):
    """Read all files in a config directory."""
    config_dir = Path(config_dir)
    files = {}
    for f in config_dir.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(config_dir))
            try:
                files[rel] = f.read_text()
            except:
                pass
    return files


def write_config(config_dir, files):
    """Write files to a config directory."""
    config_dir = Path(config_dir)
    # Clear existing
    if config_dir.exists():
        import shutil
        shutil.rmtree(config_dir)
    config_dir.mkdir(parents=True)
    for rel_path, content in files.items():
        full_path = config_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: python evolve.py <results-dir>")
        sys.exit(1)

    results_dir = Path(sys.argv[1])
    analysis_file = results_dir / "analysis.json"
    report_file = results_dir / "report.md"

    if not analysis_file.exists():
        print("No analysis.json found. Run analyze.py first.")
        sys.exit(1)

    analysis = json.loads(analysis_file.read_text())
    report = report_file.read_text() if report_file.exists() else "No report available."

    # Read all current configs
    configs = {}
    for config_dir in sorted(Path("configs").glob("*/")):
        name = config_dir.name
        configs[name] = read_config(config_dir)

    # Build prompt for Claude
    config_descriptions = []
    for name, files in sorted(configs.items()):
        desc = f"\n### {name}\n"
        for fname, content in sorted(files.items()):
            desc += f"\n**{fname}:**\n```\n{content}\n```\n"
        config_descriptions.append(desc)

    prompt = f"""You are analyzing the results of a Claude Code instruction set evaluation.

## Results
{report}

## Analysis
{json.dumps(analysis, indent=2)}

## Current Configs
{"".join(config_descriptions)}

## Task
Based on the results, generate 5 evolved config directories. Each config is a .claude/ directory with CLAUDE.md and optionally rules/, agents/, hooks/, skills/ files.

Generate the configs as a JSON object with this structure:
{{
  "configs": {{
    "A-baseline": {{ "CLAUDE.md": "content...", "rules/workflow.md": "content..." }},
    ...
  }},
  "reasoning": "Why these changes were made"
}}

Rules:
- Config E (control) should be the current best performer, unchanged
- Config A should be a minimal mutation of the best (change one thing)
- Config B should cross the best two performers
- Config C should try a structural experiment (add/remove a file type)
- Config D should be a wildcard novel approach
- Changes must be general (work for any coding task), not specific to these 3 challenges
- Keep configs concise — every line costs input tokens

Output ONLY the JSON object, no other text."""

    print("Calling claude -p for evolution analysis...")
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "1"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        print(f"Claude failed: {result.stderr}")
        sys.exit(1)

    # Parse JSON from output
    output = result.stdout.strip()

    # Try to extract JSON from the output
    try:
        # Look for JSON block
        if "```json" in output:
            json_str = output.split("```json")[1].split("```")[0]
        elif "```" in output:
            json_str = output.split("```")[1].split("```")[0]
        else:
            json_str = output

        evolved = json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Failed to parse evolution output: {e}")
        print(f"Raw output:\n{output[:500]}")
        sys.exit(1)

    # Write evolved configs
    if "configs" in evolved:
        for name, files in evolved["configs"].items():
            config_dir = Path("configs") / name
            write_config(config_dir, files)
            print(f"  Updated: {name} ({len(files)} files)")

    if "reasoning" in evolved:
        print(f"\nReasoning: {evolved['reasoning']}")

    print("\nEvolution complete.")


if __name__ == "__main__":
    main()
