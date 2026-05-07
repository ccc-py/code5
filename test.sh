#!/bin/bash
set -x

cd "$(dirname "$0")"

RUN_E2E=true
RUN_PLAYWRIGHT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-e2e)
            RUN_E2E=false
            shift
            ;;
        --no-playwright)
            RUN_PLAYWRIGHT=false
            shift
            ;;
        -h|--help)
            echo "Usage: ./test.sh [options]"
            echo ""
            echo "Options:"
            echo "  --no-e2e        Skip all E2E tests"
            echo "  --no-playwright Skip Playwright tests (still runs TestClient E2E)"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== Installing package in development mode ==="
pip3 install -e ".[dev]" -q
pip3 install playwright -q

echo "=== Running ruff linter ==="
ruff check src/ tests/ || true

echo "=== Running pytest (Unit Tests + API Tests) ==="
python3 -m pytest tests/ -v --tb=short -W ignore -k "not (TestWebE2E or TestWebE2EBrowser or TestWebPlaywright)"

if [ "$RUN_E2E" = true ]; then
    echo "=== Running E2E Tests (TestClient) ==="
    python3 -m pytest tests/test_web.py::TestWebE2E tests/test_web.py::TestWebE2EBrowser -v --tb=short -W ignore
    
    if [ "$RUN_PLAYWRIGHT" = true ]; then
        echo "=== Running E2E Tests (Playwright) ==="
        export CODE5_WEB_USE_MOCK=true
        python3 -m pytest tests/test_web.py::TestWebPlaywright -v --tb=short -W ignore
    fi
fi

echo "=== Test complete ==="