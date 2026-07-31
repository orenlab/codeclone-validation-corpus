from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_WORK_PROJECT_DIR = "project"
_WORK_ARTIFACTS = (
    "metrics-baseline.json",
    "report.json",
    "cache.json",
)
_COPY_IGNORE = shutil.ignore_patterns(".codeclone", "__pycache__", "*.pyc")
_REPORT_DEPENDENT_EXPECT_KEYS = frozenset(
    {"findings", "clones", "metrics", "inventory", "determinism"}
)

from corpus_tools.matchers import (
    FindingRef,
    active_finding_count,
    clone_group_count,
    clone_group_novelty_counts,
    dead_code_summary,
    dependency_cycle_count,
    family_group_count,
    finding_present,
    health_score,
    inventory_files,
    parse_finding_ref,
)
from corpus_tools.normalize_report import (
    determinism_projection,
    projection_digest,
)
from corpus_tools.runner import CommandResult, load_report


@dataclass(frozen=True, slots=True)
class VerificationError:
    message: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    ok: bool
    errors: tuple[VerificationError, ...] = ()


def _check_expect_block(
    report: Mapping[str, Any],
    expect: Mapping[str, Any],
    *,
    result: CommandResult,
) -> list[VerificationError]:
    errors: list[VerificationError] = []
    if "exit_code" in expect:
        expected_exit = int(expect["exit_code"])
        if result.exit_code != expected_exit:
            errors.append(
                VerificationError(
                    f"exit_code expected {expected_exit}, got {result.exit_code}"
                )
            )
    if result.report_path is None:
        if any(key in expect for key in _REPORT_DEPENDENT_EXPECT_KEYS):
            errors.append(VerificationError("report.json was not produced"))
        return errors

    findings = expect.get("findings")
    if isinstance(findings, Mapping):
        if "exact_total_active" in findings:
            expected_total = int(findings["exact_total_active"])
            actual_total = active_finding_count(report)
            if actual_total != expected_total:
                errors.append(
                    VerificationError(
                        "exact_total_active expected "
                        f"{expected_total}, got {actual_total}"
                    )
                )
        must_include = findings.get("must_include")
        if isinstance(must_include, list):
            for item in must_include:
                if not isinstance(item, Mapping):
                    continue
                ref = parse_finding_ref(item)
                if not finding_present(report, ref):
                    errors.append(
                        VerificationError(f"must_include missing: {ref}")
                    )
        must_not_include = findings.get("must_not_include")
        if isinstance(must_not_include, list):
            for item in must_not_include:
                if not isinstance(item, Mapping):
                    continue
                ref = parse_finding_ref(item)
                if finding_present(report, ref):
                    errors.append(
                        VerificationError(f"must_not_include present: {ref}")
                    )
        exact_by_kind = findings.get("exact_by_kind")
        if isinstance(exact_by_kind, Mapping):
            for key, expected in exact_by_kind.items():
                kind = str(key)
                if kind == "function":
                    actual = clone_group_count(report, "functions")
                elif kind == "block":
                    actual = clone_group_count(report, "blocks")
                elif kind == "segment":
                    actual = clone_group_count(report, "segments")
                elif kind in {"duplicated_branches", "clone_guard_exit_divergence", "clone_cohort_drift"}:
                    actual = family_group_count(report, "structural", kind=kind)
                elif kind in {
                    "function_hotspot",
                    "class_hotspot",
                    "cycle",
                    "instance_independent_method",
                    "unused_symbol",
                }:
                    if kind == "unused_symbol":
                        actual = family_group_count(report, "dead_code", kind=kind)
                    else:
                        actual = family_group_count(report, "design", kind=kind)
                else:
                    errors.append(VerificationError(f"unknown exact_by_kind key: {kind}"))
                    continue
                if actual != int(expected):
                    errors.append(
                        VerificationError(
                            f"exact_by_kind[{kind}] expected {expected}, got {actual}"
                        )
                    )

    clones = expect.get("clones")
    if isinstance(clones, Mapping):
        function_groups = clones.get("function_groups")
        if isinstance(function_groups, Mapping):
            novelty = clone_group_novelty_counts(report)
            for key in ("new", "known"):
                if key in function_groups and novelty.get(key, 0) != int(
                    function_groups[key]
                ):
                    errors.append(
                        VerificationError(
                            f"function_groups.{key} expected "
                            f"{function_groups[key]}, got {novelty.get(key, 0)}"
                        )
                    )

    metrics = expect.get("metrics")
    if isinstance(metrics, Mapping):
        cycles = metrics.get("dependency_cycles")
        if isinstance(cycles, Mapping) and "exact" in cycles:
            expected = int(cycles["exact"])
            actual = dependency_cycle_count(report)
            if actual != expected:
                errors.append(
                    VerificationError(
                        f"dependency_cycles expected {expected}, got {actual}"
                    )
                )
        health = metrics.get("health")
        if isinstance(health, Mapping) and "max_total" in health:
            actual = health_score(report)
            if actual is None or actual > int(health["max_total"]):
                errors.append(
                    VerificationError(
                        "health.total expected <= "
                        f"{health['max_total']}, got {actual}"
                    )
                )
        dead_code = metrics.get("dead_code")
        if isinstance(dead_code, Mapping):
            for key, expected in dead_code.items():
                if key == "summary" and isinstance(expected, Mapping):
                    for summary_key, summary_value in expected.items():
                        actual = dead_code_summary(report, str(summary_key))
                        if actual != int(summary_value):
                            errors.append(
                                VerificationError(
                                    "dead_code.summary."
                                    f"{summary_key} expected {summary_value}, "
                                    f"got {actual}"
                                )
                            )

    inventory = expect.get("inventory")
    if isinstance(inventory, Mapping):
        files = inventory_files(report)
        for key, expected in inventory.items():
            if key not in files:
                errors.append(VerificationError(f"inventory.files missing key: {key}"))
                continue
            if int(files[key]) != int(expected):
                errors.append(
                    VerificationError(
                        f"inventory.files.{key} expected {expected}, got {files[key]}"
                    )
                )
    return errors


def verify_single_run(
    *,
    report: Mapping[str, Any],
    expect: Mapping[str, Any],
    result: CommandResult,
    prior_projection: str | None = None,
) -> VerificationResult:
    errors = _check_expect_block(report, expect, result=result)
    determinism = expect.get("determinism")
    if isinstance(determinism, Mapping):
        projection = determinism_projection(report)
        digest = projection_digest(projection)
        if determinism.get("semantic_projection_stable") and prior_projection is not None:
            if digest != prior_projection:
                errors.append(
                    VerificationError("semantic_projection_stable check failed")
                )
    return VerificationResult(ok=not errors, errors=tuple(errors))


def _remove_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()


def _copy_fixture_tree(source: Path, destination: Path) -> Path:
    if destination.exists():
        _remove_tree(destination)
    shutil.copytree(source, destination, ignore=_COPY_IGNORE)
    return destination


def _reset_workflow_work_dir(work_dir: Path) -> None:
    for name in _WORK_ARTIFACTS:
        artifact = work_dir / name
        if artifact.is_file():
            artifact.unlink()
    project_root = work_dir / _WORK_PROJECT_DIR
    if project_root.exists():
        _remove_tree(project_root)


def _resolve_workflow_fixture_root(
    *,
    repo_root: Path,
    scenario_path: str,
    work_dir: Path,
    fixture_name: str,
    use_work_copy: bool,
    overlay: str | None,
) -> Path:
    if not use_work_copy:
        fixture_root = repo_root / scenario_path
        if fixture_name != "root":
            fixture_root = fixture_root / fixture_name
        return fixture_root

    project_root = work_dir / _WORK_PROJECT_DIR
    if overlay is not None:
        overlay_root = repo_root / scenario_path / overlay
        return _copy_fixture_tree(overlay_root, project_root)
    source = repo_root / scenario_path
    if fixture_name != "root":
        source = source / fixture_name
    return _copy_fixture_tree(source, project_root)


def verify_expectation_file(
    *,
    repo_root: Path,
    expectation_path: Path,
    codeclone_command: str,
    work_root: Path,
) -> VerificationResult:
    import json

    from corpus_tools.runner import run_codeclone

    payload = json.loads(expectation_path.read_text(encoding="utf-8"))
    kind = str(payload.get("kind", "single_run"))
    scenario_id = str(payload.get("scenario_id", expectation_path.stem))
    work_dir = work_root / scenario_id
    work_dir.mkdir(parents=True, exist_ok=True)

    if kind == "workflow":
        steps = payload.get("steps")
        if not isinstance(steps, list):
            return VerificationResult(
                ok=False,
                errors=(VerificationError("workflow expectation missing steps"),),
            )
        errors: list[VerificationError] = []
        uses_work_copy = any(
            isinstance(step, Mapping) and step.get("use_work_copy") is True
            for step in steps
        )
        if uses_work_copy:
            _reset_workflow_work_dir(work_dir)
        for step in steps:
            if not isinstance(step, Mapping):
                continue
            step_id = str(step.get("id", "step"))
            fixture_name = str(step.get("fixture", "root"))
            scenario_path = payload.get("scenario_path")
            if not isinstance(scenario_path, str):
                errors.append(VerificationError(f"{scenario_id}: missing scenario_path"))
                break
            overlay = step.get("overlay")
            overlay_name = str(overlay) if isinstance(overlay, str) else None
            use_work_copy = step.get("use_work_copy") is True
            fixture_root = _resolve_workflow_fixture_root(
                repo_root=repo_root,
                scenario_path=scenario_path,
                work_dir=work_dir,
                fixture_name=fixture_name,
                use_work_copy=use_work_copy,
                overlay=overlay_name,
            )
            cli = step.get("cli")
            extra_args: list[str] = []
            if isinstance(cli, Mapping):
                raw_args = cli.get("extra_args")
                if isinstance(raw_args, list):
                    extra_args = [str(item) for item in raw_args]
            result = run_codeclone(
                codeclone_command=codeclone_command,
                fixture_root=fixture_root,
                work_dir=work_dir,
                extra_args=extra_args,
            )
            expect = step.get("expect")
            if not isinstance(expect, Mapping):
                errors.append(VerificationError(f"{step_id}: missing expect"))
                continue
            report = (
                load_report(result.report_path)
                if result.report_path is not None
                else {}
            )
            step_errors = _check_expect_block(report, expect, result=result)
            errors.extend(
                VerificationError(f"{scenario_id}/{step_id}: {err.message}")
                for err in step_errors
            )
        return VerificationResult(ok=not errors, errors=tuple(errors))

    scenario_path = payload.get("scenario_path")
    if not isinstance(scenario_path, str):
        return VerificationResult(
            ok=False,
            errors=(VerificationError(f"{scenario_id}: missing scenario_path"),),
        )
    fixture_root = repo_root / scenario_path
    cli = payload.get("cli")
    extra_args: list[str] = []
    if isinstance(cli, Mapping):
        raw_args = cli.get("extra_args")
        if isinstance(raw_args, list):
            extra_args = [str(item) for item in raw_args]
    result = run_codeclone(
        codeclone_command=codeclone_command,
        fixture_root=fixture_root,
        work_dir=work_dir,
        extra_args=extra_args,
    )
    if result.report_path is None:
        expect = payload.get("expect")
        expect_map = expect if isinstance(expect, Mapping) else {}
        errors = _check_expect_block({}, expect_map, result=result)
        return VerificationResult(ok=not errors, errors=tuple(errors))
    report = load_report(result.report_path)
    expect = payload.get("expect")
    expect_map = expect if isinstance(expect, Mapping) else {}

    projection = determinism_projection(report)
    digest = projection_digest(projection)
    first = verify_single_run(
        report=report,
        expect=expect_map,
        result=result,
        prior_projection=None,
    )
    if not first.ok:
        return first
    determinism = expect_map.get("determinism")
    if isinstance(determinism, Mapping) and determinism.get("semantic_projection_stable"):
        second = run_codeclone(
            codeclone_command=codeclone_command,
            fixture_root=fixture_root,
            work_dir=work_dir / "repeat",
            extra_args=extra_args,
        )
        if second.report_path is None:
            return VerificationResult(
                ok=False,
                errors=(VerificationError("determinism rerun produced no report"),),
            )
        repeat_report = load_report(second.report_path)
        repeat_digest = projection_digest(determinism_projection(repeat_report))
        if repeat_digest != digest:
            return VerificationResult(
                ok=False,
                errors=(VerificationError("semantic_projection_stable failed on rerun"),),
            )
    return first
