#!/bin/bash
set -x

cd "$(dirname "$0")"

echo "=== Installing package in development mode ==="
pip install -e ".[dev]" -q

echo "=== Running ruff linter ==="
ruff check src/ tests/ || true

echo "=== Running pytest ==="
python -m pytest tests/ -v --tb=short

echo "=== Test complete ==="