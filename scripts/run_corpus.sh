#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODECLONE_COMMAND="${CODECLONE_COMMAND:-uv run --directory "${CODECLONE_ROOT:-$ROOT/../codeclone}" codeclone}"
cd "$ROOT"
uv sync --quiet
uv run python -m corpus_tools.cli "$@" --codeclone-command "$CODECLONE_COMMAND"
