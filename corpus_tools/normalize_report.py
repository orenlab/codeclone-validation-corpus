from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

# Fields stripped for semantic projection (documented contract; not ad-hoc scrubbing).
_META_VOLATILE_KEYS = frozenset(
    {
        "runtime",
        "cache_path",
        "cache_used",
        "cache_status",
        "generated_at",
        "analysis_started_at",
        "analysis_finished_at",
    }
)


def _strip_display_facts(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_display_facts(item)
            for key, item in value.items()
            if str(key) != "display_facts"
        }
    if isinstance(value, list):
        return [_strip_display_facts(item) for item in value]
    return value


def semantic_projection(report: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic semantic view of a canonical CodeClone report."""
    meta = report.get("meta")
    meta_map = meta if isinstance(meta, Mapping) else {}
    canonical_meta = {
        str(key): value
        for key, value in meta_map.items()
        if str(key) not in _META_VOLATILE_KEYS
    }
    findings = report.get("findings")
    findings_map = findings if isinstance(findings, Mapping) else {}
    metrics = report.get("metrics")
    metrics_map = metrics if isinstance(metrics, Mapping) else {}
    inventory = report.get("inventory")
    inventory_map = inventory if isinstance(inventory, Mapping) else {}
    return {
        "report_schema_version": str(report.get("report_schema_version", "")),
        "meta": canonical_meta,
        "inventory": json.loads(json.dumps(inventory_map, sort_keys=True)),
        "findings": _strip_display_facts(findings_map),
        "metrics": json.loads(json.dumps(metrics_map, sort_keys=True)),
    }


def determinism_projection(report: Mapping[str, Any]) -> dict[str, Any]:
    """Stable subset for rerun checks (excludes cache/inventory counters)."""
    full = semantic_projection(report)
    return {
        "report_schema_version": full["report_schema_version"],
        "findings": full["findings"],
        "metrics": full["metrics"],
    }


def projection_digest(projection: Mapping[str, Any]) -> str:
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    return payload
