#!/bin/bash
set -x

cd "$(dirname "$0")"

SHOW_BROWSER=false
RUN_BROWSER_TESTS=true
RUN_PLAYWRIGHT_TESTS=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --show-browser)
            SHOW_BROWSER=true
            shift
            ;;
        --no-browser)
            RUN_BROWSER_TESTS=false
            shift
            ;;
        --no-playwright)
            RUN_PLAYWRIGHT_TESTS=false
            shift
            ;;
        -h|--help)
            echo "Usage: ./e2e.sh [options]"
            echo ""
            echo "Options:"
            echo "  --show-browser    Show browser (for Playwright tests)"
            echo "  --no-browser      Skip TestClient browser tests"
            echo "  --no-playwright   Skip Playwright tests"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== Running E2E Tests ==="
echo "Show browser: $SHOW_BROWSER"
echo "Run browser tests (TestClient): $RUN_BROWSER_TESTS"
echo "Run Playwright tests: $RUN_PLAYWRIGHT_TESTS"

echo "=== Installing package in development mode ==="
pip3 install -e ".[dev]" -q
pip3 install playwright -q

TESTS="tests/test_web.py::TestWebE2E"

if [ "$RUN_BROWSER_TESTS" = true ]; then
    TESTS="$TESTS tests/test_web.py::TestWebE2EBrowser"
fi

if [ "$RUN_PLAYWRIGHT_TESTS" = true ]; then
    if [ "$SHOW_BROWSER" = true ]; then
        export PLAYWRIGHT_HEADLESS=false
        echo "=== Running Playwright tests with visible browser ==="
    else
        export PLAYWRIGHT_HEADLESS=true
        echo "=== Running Playwright tests (headless) ==="
    fi
    
    echo "=== Starting web server in background ==="
    python3 -m code5.web --mock --port 8000 &
    SERVER_PID=$!
    sleep 3
    
    echo "=== Running Playwright tests ==="
    TESTS="$TESTS tests/test_web.py::TestWebPlaywright"
    
    kill $SERVER_PID 2>/dev/null || true
fi

echo "=== Running E2E tests ==="
python3 -m pytest $TESTS -v --tb=short -W ignore

echo "=== E2E Tests complete ==="