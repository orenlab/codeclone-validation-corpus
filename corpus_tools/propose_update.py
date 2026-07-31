from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_tools.normalize_report import semantic_projection
from corpus_tools.runner import load_report, run_codeclone
from corpus_tools.verify_expectation import verify_single_run
from corpus_tools.runner import CommandResult


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Propose an expectation update candidate (never auto-approves)"
    )
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--codeclone-command",
        default="codeclone",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    manifest = json.loads((repo_root / "corpus" / "manifest.json").read_text())
    entry = next(
        item
        for item in manifest["scenarios"]
        if item["id"] == args.scenario
    )
    expectation_path = repo_root / entry["expectation"]
    expectation = json.loads(expectation_path.read_text())
    if expectation.get("kind") != "single_run":
        raise SystemExit("propose update supports single_run expectations only")
    fixture_root = repo_root / expectation["scenario_path"]
    work_dir = repo_root / "work" / f"{args.scenario}-proposal"
    cli = expectation.get("cli", {})
    extra_args = cli.get("extra_args", [])
    result = run_codeclone(
        codeclone_command=args.codeclone_command,
        fixture_root=fixture_root,
        work_dir=work_dir,
        extra_args=extra_args,
    )
    if result.report_path is None:
        raise SystemExit("CodeClone did not produce report.json")
    report = load_report(result.report_path)
    candidate = dict(expectation)
    candidate["expect"] = {
        "exit_code": result.exit_code,
        "findings": {
            "exact_total_active": 0,
            "note": "maintainer must fill closed-world assertions manually",
        },
        "determinism": {"semantic_projection_stable": True},
        "_evidence": {
            "semantic_projection": semantic_projection(report),
        },
    }
    output = Path(args.output)
    output.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
    print(f"candidate written: {output}")
    print("Review manually; do not auto-approve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
