#!/bin/bash
set -x

cd "$(dirname "$0")"

RUN_LLM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --llm)
            RUN_LLM=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./test_blog.sh [options]"
            echo ""
            echo "Options:"
            echo "  --llm          Run with real LLM (requires NVIDIA_API_KEY)"
            echo "  -h, --help     Show this help"
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

echo "=== Running ruff linter ==="
ruff check src/ tests/test_blog.py || true

echo "=== Running blog tests (Mock mode) ==="
python3 -m pytest tests/test_blog.py -v --tb=short -W ignore

if [ "$RUN_LLM" = true ]; then
    echo ""
    echo "=== Running blog tests (Real LLM mode) ==="
    TEST_LLM=1 python3 -m pytest tests/test_blog.py::TestFastAPIBlog -v --tb=short -W ignore
fi

echo ""
echo "=== Test complete ==="
