"""Web interface entry point for code5."""

import argparse
import os

import uvicorn


def main() -> None:
    """Run the FastAPI web server."""
    parser = argparse.ArgumentParser(description="Code5 Web Server")
    parser.add_argument(
        "--mock",
        action="store_true",
        default=None,
        help="Use mock LLM client",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use real LLM (NVIDIA API)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)",
    )
    args = parser.parse_args()

    use_mock = args.mock if args.mock is not None else not args.llm
    os.environ["CODE5_WEB_USE_MOCK"] = "true" if use_mock else "false"

    print(f"Starting Code5 Web Server (mode: {'MOCK' if use_mock else 'LLM'})")
    print(f"Server: http://{args.host}:{args.port}")

    uvicorn.run(
        "code5.web.app:app",
        host=args.host,
        port=args.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
