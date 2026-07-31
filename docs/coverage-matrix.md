# CodeClone validation corpus — coverage matrix

Black-box acceptance over the **public CLI only**. Expectations are semantic (subjects, counts, exit codes), not full
report goldens.

Source of truth for gate flags: `tests/fixtures/contract_snapshots/cli_help.txt` (Quality gates section) and
`docs/book/16-metrics-and-quality-gates.md` in the CodeClone repository.

## Tiers

| Tier    | Count | When to run                                      |
|---------|-------|--------------------------------------------------|
| `smoke` | 10    | PRs, quick regression                            |
| `gates` | 20    | Quality-gate conformance (`--tier gates`)        |
| `full`  | 13    | Detection / structural / governance beyond gates |
| `all`   | 34    | Full conformance (`--tier all`)                  |

## Quality gates (`gates` tier)

Every public **Quality gates** flag from CLI help has at least one corpus scenario.

| CLI flag | Exit | Scenario | Notes |
|----------|------|----------|-------|
| `--fail-on-new` | 3 | G01 (smoke) | Clone baseline workflow |
| `--fail-on-new-metrics` | 3 | M10 | Metrics baseline + new dead code |
| `--fail-on-new-metrics` | 2 | C02 | No metrics baseline loaded |
| `--fail-threshold` | 3 | M03 | Total clone groups |
| `--fail-complexity` | 3 | M05 | CC threshold |
| `--fail-coupling` | 3 | M06 | CBO via in-module class references |
| `--fail-cohesion` | 3 | M07 | LCOM4 via disconnected methods |
| `--fail-cycles` | 3 | M01 (smoke) | Circular imports |
| `--fail-dead-code` | 3 | M02 | High-confidence dead code |
| `--fail-health` | 3 | M04 | Health score floor |
| `--fail-on-typing-regression` | 3 | M11 | Metrics baseline delta |
| `--fail-on-typing-regression` | 2 | C05 | No metrics baseline |
| `--fail-on-docstring-regression` | 3 | M12 | Metrics baseline delta |
| `--fail-on-docstring-regression` | 2 | C06 | No metrics baseline |
| `--fail-on-api-break` | 3 | M13 | Public API removal |
| `--fail-on-api-break` | 2 | C07 | No metrics baseline |
| `--fail-on-untested-hotspots` | 3 | M14 | Requires `--coverage` |
| `--fail-on-untested-hotspots` | 2 | C04 | Missing `--coverage` |
| `--min-typing-coverage` | 3 | M08 | Parameter typing floor |
| `--min-docstring-coverage` | 3 | M09 | Public docstring floor |
| `--coverage-min` | 3 | M14 | Used with coverage join + hotspots |
| `--ci` | 2 | G06 (full) | Untrusted / missing clone baseline |

### Gate contract conflicts (`gates` tier)

| Condition | Exit | Scenario |
|-----------|------|----------|
| `--skip-metrics` + `--fail-dead-code` | 2 | C03 |
| `--skip-metrics` + `--update-metrics-baseline` | 2 | C08 |

## Smoke (10)

| ID  | Lane              | Capability                       |
|-----|-------------------|----------------------------------|
| D01 | detection         | Identical function clone         |
| D02 | detection         | Parameter-renamed function clone |
| D03 | detection         | Cross-function block clone       |
| D04 | detection         | Unused function (dead code)      |
| N01 | negative-controls | Near-duplicate negative          |
| N02 | negative-controls | Block threshold negative         |
| N03 | negative-controls | Reachable entrypoint negative    |
| G01 | governance        | Baseline known vs new workflow   |
| M01 | metrics           | Dependency cycle gate            |
| C01 | contracts         | Parse error partial success      |

## Full (+13, non-gate capabilities)

| ID  | Lane       | Capability                                       |
|-----|------------|--------------------------------------------------|
| D05 | detection  | Multi block clone groups                         |
| D08 | detection  | Complexity design hotspot                        |
| D11 | detection  | Design cycle finding                             |
| S01 | structural | Duplicated branches                              |
| S04 | structural | No structural findings                           |
| G02 | governance | Baseline roundtrip (no new)                      |
| G05 | governance | Inline dead-code suppression                     |
| G06 | governance | CI untrusted baseline                            |

## Not yet covered (future extended tier)

- `--update-metrics-baseline` contract conflict with `--skip-metrics` (exit 2)
- `--ci` auto-enabling `--fail-on-new-metrics` when trusted metrics baseline is present
- Segment clone groups (`findings.groups.clones.segments` — empty on 2.1.0a1 defaults)
- Clone cohort drift / guard exit divergence (S02–S03)
- Golden-fixture suppressed clones (G04)
- Metrics baseline delta workflow beyond dead code / adoption / API (G03)
- Changed-only / patch-verify gate combinations

## Metrics baseline workflows

Scenarios M10–M13 use `use_work_copy` + `overlay` so both steps analyze the **same directory path**. Metrics baselines
store absolute file paths from the scan root; stale `work/*/metrics-baseline.json` or fixture `.codeclone/` caches from
earlier runs must not be reused — the runner resets `work/<scenario>/` before each workflow.
