from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Closed allowlist of public CodeClone CLI flags the corpus may append.
#
# The metrics baseline no longer has its own file or its own flags: it is one
# lane inside the v3 baseline container, so --metrics-baseline and
# --update-metrics-baseline were removed from the public CLI and must not be
# reintroduced here. Use --baseline / --update-baseline for every lane.
ALLOWED_CODECLONE_ARGS = frozenset(
    {
        "--json",
        "--no-progress",
        "--no-color",
        "--baseline",
        "--update-baseline",
        "--fail-on-new",
        "--fail-cycles",
        "--fail-dead-code",
        "--ci",
        "--skip-metrics",
        "--fail-threshold",
        "--cache-path",
        "--api-surface",
        "--fail-on-new-metrics",
        "--fail-health",
        "--fail-complexity",
        "--fail-cohesion",
        "--fail-coupling",
        "--min-loc",
        "--min-stmt",
        "--coverage",
        "--coverage-min",
        "--fail-on-typing-regression",
        "--fail-on-docstring-regression",
        "--fail-on-api-break",
        "--fail-on-untested-hotspots",
        "--min-typing-coverage",
        "--min-docstring-coverage",
    }
)


def _strip_json_args(args: Sequence[str]) -> list[str]:
    filtered: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--json":
            skip_next = True
            continue
        if arg.startswith("--json="):
            continue
        filtered.append(arg)
    return filtered


@dataclass(frozen=True, slots=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    report_path: Path | None


def _expand(template: str, *, work_dir: Path, fixture_root: Path) -> str:
    return (
        template.replace("{work}", str(work_dir)).replace("{scenario}", str(fixture_root))
    )


def expand_args(
    args: Sequence[str],
    *,
    work_dir: Path,
    fixture_root: Path,
) -> list[str]:
    expanded: list[str] = []
    for arg in args:
        value = _expand(arg, work_dir=work_dir, fixture_root=fixture_root)
        flag = value.split("=", 1)[0] if value.startswith("--") else value
        if value.startswith("--") and flag not in ALLOWED_CODECLONE_ARGS:
            raise ValueError(f"Disallowed CodeClone arg: {value}")
        expanded.append(value)
    return expanded


def run_codeclone(
    *,
    codeclone_command: str,
    fixture_root: Path,
    work_dir: Path,
    extra_args: Sequence[str],
) -> CommandResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    report_path = work_dir / "report.json"
    cache_path = work_dir / "cache.json"
    cache_path.unlink(missing_ok=True)
    user_args = _strip_json_args(
        expand_args(list(extra_args), work_dir=work_dir, fixture_root=fixture_root)
    )
    command = [
        *shlex.split(codeclone_command),
        str(fixture_root),
        "--json",
        str(report_path),
        "--cache-path",
        str(cache_path),
        "--no-progress",
        "--no-color",
        *user_args,
    ]
    env = os.environ.copy()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    parsed_report: Path | None = report_path if report_path.is_file() else None
    return CommandResult(
        exit_code=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
        report_path=parsed_report,
    )


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
