# CodeClone Validation Corpus

External black-box acceptance corpus for the **public CodeClone CLI**.

This repository is a small conformance framework, not a golden snapshot dump:

- public CLI only (closed allowlist of flags)
- semantic expectations (subjects, exit codes, closed-world counts)
- multi-step workflows for baseline governance
- normalized semantic projection for determinism checks
- no MCP, no internal Python APIs

## Layout

```text
corpus/manifest.json          scenario registry
corpus/scenarios/             synthetic mini-projects by lane
expectations/                   JSON expectation contracts
corpus_tools/                   runner + verifier
scripts/run_corpus.sh           local entrypoint
```

## Quick start

From this repository:

```bash
chmod +x scripts/run_corpus.sh
./scripts/run_corpus.sh --tier smoke
```

By default the runner uses CodeClone from the sibling checkout:

```text
../codeclone
```

Override:

```bash
export CODECLONE_ROOT=/path/to/codeclone
export CODECLONE_COMMAND="codeclone"   # published wheel on PATH
./scripts/run_corpus.sh --tier smoke
```

Run one scenario:

```bash
./scripts/run_corpus.sh --scenario D01-identical-function-clone
```

Run full conformance (smoke + full):

```bash
./scripts/run_corpus.sh --tier all
```

Run full tier only:

```bash
./scripts/run_corpus.sh --tier full
```

Run quality-gate conformance (maps 1:1 to CLI help **Quality gates**):

```bash
./scripts/run_corpus.sh --tier gates
```

Coverage map: [docs/coverage-matrix.md](docs/coverage-matrix.md).

## Smoke scenarios (10)

| ID  | Lane              | Signal                           |
|-----|-------------------|----------------------------------|
| D01 | detection         | identical function clone         |
| D02 | detection         | parameter-renamed function clone |
| D03 | detection         | cross-function block clone       |
| D04 | detection         | unused function (dead code)      |
| N01 | negative-controls | near-duplicate negative          |
| N02 | negative-controls | block threshold negative         |
| N03 | negative-controls | reachable entrypoint negative    |
| G01 | governance        | baseline known/new workflow      |
| M01 | metrics           | dependency cycle gate            |
| C01 | contracts         | parse error partial success      |

## Gates tier (20)

All public `--fail-*`, `--min-*-coverage`, and `--fail-on-*` quality gates from CLI help, plus contract conflicts when
metrics flags are incompatible with `--skip-metrics`. See the full checklist in
[docs/coverage-matrix.md](docs/coverage-matrix.md).

## Full tier (+13)

Design hotspots, structural findings, governance (baseline roundtrip, inline suppression, CI baseline trust). Metric
gate scenarios live in the `gates` tier. See [docs/coverage-matrix.md](docs/coverage-matrix.md).

## Expectation updates

Never auto-approve truth. Generate a candidate only:

```bash
uv run python -m corpus_tools.propose_update \
  --scenario D01-identical-function-clone \
  --output /tmp/D01.candidate.json
```

Review old expectation, candidate, and normalized evidence manually before merge.

## CI policy (recommended)

| Trigger                    | CodeClone source        | Tier        |
|----------------------------|-------------------------|-------------|
| PR in this repo            | latest prerelease wheel | smoke       |
| PR in this repo (gates)    | latest prerelease wheel | gates       |
| PR in CodeClone main       | wheel from that commit  | smoke       |
| release candidate / manual | RC artifact             | full or all |

## Compatibility

Manifest documents minimum corpus compatibility:

```json
"compatibility": {
"minimum_codeclone": "2.1.0a1",
"minimum_report_schema": "2.11"
}
```

The tested binary version is chosen by CI, not embedded as a semver constraint on scenarios.

## License

Mozilla Public License 2.0 (same family as CodeClone).
