from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SubjectRef:
    relative_path: str
    qualname: str


@dataclass(frozen=True, slots=True)
class FindingRef:
    family: str
    kind: str
    subjects: tuple[SubjectRef, ...] = ()
    path: str = ""
    qualname: str = ""
    confidence: str = ""
    severity: str = ""


def _clone_groups(report: Mapping[str, Any], clone_kind: str) -> list[Mapping[str, Any]]:
    findings = report.get("findings")
    if not isinstance(findings, Mapping):
        return []
    groups = findings.get("groups")
    if not isinstance(groups, Mapping):
        return []
    clones = groups.get("clones")
    if not isinstance(clones, Mapping):
        return []
    bucket = clones.get(clone_kind)
    if not isinstance(bucket, Sequence):
        return []
    return [group for group in bucket if isinstance(group, Mapping)]


def _flat_groups(report: Mapping[str, Any], family: str) -> list[Mapping[str, Any]]:
    findings = report.get("findings")
    if not isinstance(findings, Mapping):
        return []
    groups_root = findings.get("groups")
    if not isinstance(groups_root, Mapping):
        return []
    if family == "clones":
        out: list[Mapping[str, Any]] = []
        clones = groups_root.get("clones")
        if isinstance(clones, Mapping):
            for key in ("functions", "blocks", "segments"):
                bucket = clones.get(key)
                if isinstance(bucket, Sequence):
                    out.extend(item for item in bucket if isinstance(item, Mapping))
        return out
    family_payload = groups_root.get(family)
    if not isinstance(family_payload, Mapping):
        return []
    bucket = family_payload.get("groups")
    if not isinstance(bucket, Sequence):
        return []
    return [group for group in bucket if isinstance(group, Mapping)]


def active_finding_count(report: Mapping[str, Any]) -> int:
    total = 0
    for family in ("clones", "structural", "dead_code", "design"):
        total += len(_flat_groups(report, family))
    return total


# Only these two novelty values are evidence about a group's novelty. Anything
# else -- an absent field, an empty string, the engine's own "unavailable" lane
# signal, or a token this corpus does not know -- means the report cannot tell
# us whether the group is new, and must never be tallied as "known".
_NOVELTY_NEW = "new"
_NOVELTY_KNOWN = "known"
_NOVELTY_ABSENT = "<absent>"


@dataclass(frozen=True, slots=True)
class NoveltyTally:
    """Novelty counts alongside the groups that carried no novelty evidence.

    ``unevidenced`` is a sorted (token, count) breakdown so callers can name
    what the report actually said instead of guessing.
    """

    new: int = 0
    known: int = 0
    unevidenced: tuple[tuple[str, int], ...] = ()

    @property
    def unevidenced_total(self) -> int:
        return sum(count for _, count in self.unevidenced)

    @property
    def total(self) -> int:
        return self.new + self.known + self.unevidenced_total

    @property
    def evaluable(self) -> bool:
        """True when every group carried a novelty value we can trust."""
        return not self.unevidenced

    def count(self, key: str) -> int:
        return self.new if key == _NOVELTY_NEW else self.known

    def describe_unevidenced(self) -> str:
        return ", ".join(f"{token}={count}" for token, count in self.unevidenced)


def clone_group_novelty_tally(report: Mapping[str, Any]) -> NoveltyTally:
    new = 0
    known = 0
    unevidenced: dict[str, int] = {}
    for group in _clone_groups(report, "functions"):
        raw = group.get("novelty")
        token = _NOVELTY_ABSENT if raw is None else str(raw).strip()
        if token == _NOVELTY_NEW:
            new += 1
        elif token == _NOVELTY_KNOWN:
            known += 1
        else:
            key = token or _NOVELTY_ABSENT
            unevidenced[key] = unevidenced.get(key, 0) + 1
    return NoveltyTally(
        new=new,
        known=known,
        unevidenced=tuple(sorted(unevidenced.items())),
    )


def clone_group_count(report: Mapping[str, Any], clone_kind: str) -> int:
    return len(_clone_groups(report, clone_kind))


def inventory_files(report: Mapping[str, Any]) -> Mapping[str, Any]:
    inventory = report.get("inventory")
    if not isinstance(inventory, Mapping):
        return {}
    files = inventory.get("files")
    return files if isinstance(files, Mapping) else {}


def dependency_cycle_count(report: Mapping[str, Any]) -> int:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return 0
    families = metrics.get("families")
    if not isinstance(families, Mapping):
        return 0
    deps = families.get("dependencies")
    if not isinstance(deps, Mapping):
        return 0
    summary = deps.get("summary")
    if not isinstance(summary, Mapping):
        return 0
    value = summary.get("cycles", 0)
    return int(value) if isinstance(value, int) else 0


def health_score(report: Mapping[str, Any]) -> int | None:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return None
    families = metrics.get("families")
    if not isinstance(families, Mapping):
        return None
    health = families.get("health")
    if not isinstance(health, Mapping):
        return None
    summary = health.get("summary")
    if not isinstance(summary, Mapping):
        return None
    total = summary.get("score", summary.get("total"))
    return int(total) if isinstance(total, int) else None


def dead_code_summary(report: Mapping[str, Any], key: str) -> int:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return 0
    families = metrics.get("families")
    if not isinstance(families, Mapping):
        return 0
    dead_code = families.get("dead_code")
    if not isinstance(dead_code, Mapping):
        return 0
    summary = dead_code.get("summary")
    if not isinstance(summary, Mapping):
        return 0
    value = summary.get(key, 0)
    return int(value) if isinstance(value, int) else 0


def family_group_count(
    report: Mapping[str, Any],
    family: str,
    *,
    kind: str = "",
) -> int:
    groups = _flat_groups(report, family)
    if not kind:
        return len(groups)
    return sum(1 for group in groups if str(group.get("kind", "")) == kind)


def _group_subjects(group: Mapping[str, Any]) -> set[tuple[str, str]]:
    items = group.get("items")
    if not isinstance(items, Sequence):
        return set()
    out: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        out.add((str(item.get("relative_path", "")), str(item.get("qualname", ""))))
    return out


def _group_matches(ref: FindingRef, group: Mapping[str, Any]) -> bool:
    if ref.family == "clones":
        if ref.kind:
            clone_kind = str(group.get("clone_kind", group.get("kind", "")))
            if clone_kind != ref.kind and str(group.get("kind", "")) != ref.kind:
                return False
        if ref.subjects:
            subjects = _group_subjects(group)
            required = {(s.relative_path, s.qualname) for s in ref.subjects}
            return required.issubset(subjects)
        return True
    if ref.kind and str(group.get("kind", "")) != ref.kind:
        return False
    if ref.severity and str(group.get("severity", "")) != ref.severity:
        return False
    items = group.get("items")
    if not isinstance(items, Sequence) or not items:
        return True
    first = items[0]
    if not isinstance(first, Mapping):
        return False
    if ref.path and str(first.get("relative_path", "")) != ref.path:
        return False
    if ref.qualname and str(first.get("qualname", "")) != ref.qualname:
        return False
    if ref.confidence and str(group.get("confidence", "")) != ref.confidence:
        return False
    return True


def finding_present(report: Mapping[str, Any], ref: FindingRef) -> bool:
    groups = _flat_groups(report, ref.family)
    if not ref.kind and not ref.subjects and not ref.path and not ref.qualname:
        return bool(groups)
    return any(_group_matches(ref, group) for group in groups)


def parse_finding_ref(payload: Mapping[str, Any]) -> FindingRef:
    subjects_payload = payload.get("subjects")
    subjects: tuple[SubjectRef, ...] = ()
    if isinstance(subjects_payload, Sequence):
        parsed: list[SubjectRef] = []
        for item in subjects_payload:
            if isinstance(item, Sequence) and len(item) == 2:
                parsed.append(SubjectRef(str(item[0]), str(item[1])))
        subjects = tuple(parsed)
    return FindingRef(
        family=str(payload.get("family", "")),
        kind=str(payload.get("kind", "")),
        subjects=subjects,
        path=str(payload.get("path", "")),
        qualname=str(payload.get("qualname", "")),
        confidence=str(payload.get("confidence", "")),
        severity=str(payload.get("severity", "")),
    )
