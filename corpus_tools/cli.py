from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corpus_tools.verify_expectation import VerificationResult, verify_expectation_file


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_manifest(repo_root: Path) -> dict[str, object]:
    manifest_path = repo_root / "corpus" / "manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _tier_matches(item_tier: str, requested: str | None) -> bool:
    if requested is None or requested == "all":
        return True
    if requested == "full":
        return item_tier in {"full", "gates"}
    return item_tier == requested


def _scenario_entries(manifest: dict[str, object], tier: str | None) -> list[dict[str, object]]:
    scenarios = manifest.get("scenarios")
    if not isinstance(scenarios, list):
        raise SystemExit("manifest.scenarios must be a list")
    selected: list[dict[str, object]] = []
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        if tier is not None and not _tier_matches(str(item.get("tier", "")), tier):
            continue
        selected.append(item)
    return selected


def _print_result(scenario_id: str, result: VerificationResult) -> None:
    if result.ok:
        print(f"PASS {scenario_id}")
        return
    print(f"FAIL {scenario_id}", file=sys.stderr)
    for error in result.errors:
        print(f"  - {error.message}", file=sys.stderr)


def run_corpus(
    *,
    repo_root: Path,
    codeclone_command: str,
    tier: str | None,
    scenario_id: str | None,
    work_root: Path,
) -> int:
    manifest = _load_manifest(repo_root)
    entries = _scenario_entries(manifest, tier)
    if scenario_id is not None:
        entries = [item for item in entries if str(item.get("id", "")) == scenario_id]
    if not entries:
        print("No scenarios selected.", file=sys.stderr)
        return 2
    failures = 0
    for entry in entries:
        sid = str(entry.get("id", "unknown"))
        expectation_rel = str(entry.get("expectation", ""))
        expectation_path = repo_root / expectation_rel
        result = verify_expectation_file(
            repo_root=repo_root,
            expectation_path=expectation_path,
            codeclone_command=codeclone_command,
            work_root=work_root,
        )
        _print_result(sid, result)
        if not result.ok:
            failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CodeClone validation corpus")
    parser.add_argument(
        "--codeclone-command",
        default="codeclone",
        help="CodeClone CLI command (default: codeclone on PATH)",
    )
    parser.add_argument(
        "--tier",
        default="smoke",
        help="Scenario tier filter: smoke, gates, full, all (default: smoke)",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a single scenario id",
    )
    parser.add_argument(
        "--work-root",
        default=None,
        help="Temporary work directory root (default: repo_root/work)",
    )
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    work_root = Path(args.work_root) if args.work_root else repo_root / "work"
    return run_corpus(
        repo_root=repo_root,
        codeclone_command=args.codeclone_command,
        tier=args.tier,
        scenario_id=args.scenario,
        work_root=work_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
