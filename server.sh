#!/bin/bash
cd "$(dirname "$0")"

# Parse arguments
MOCK_MODE=""
HOST="0.0.0.0"
PORT=8000

while [[ $# -gt 0 ]]; do
    case $1 in
        --mock)
            MOCK_MODE="--mock"
            shift
            ;;
        --llm)
            MOCK_MODE="--llm"
            shift
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Usage: ./server.sh [--mock|--llm] [--host HOST] [--port PORT]"
            exit 1
            ;;
    esac
done

# If no explicit mode, auto-detect based on NVIDIA_API_KEY
if [ -z "$MOCK_MODE" ]; then
    if [ -n "$NVIDIA_API_KEY" ]; then
        MOCK_MODE="--llm"
    else
        MOCK_MODE="--mock"
    fi
fi

echo "=== Starting Code5 Web Server ==="
echo "Mode: $([ "$MOCK_MODE" = "--mock" ] && echo "MOCK" || echo "LLM")"
echo "Server: http://$HOST:$PORT"
echo ""

python3 -m code5.web $MOCK_MODE --host "$HOST" --port "$PORT"