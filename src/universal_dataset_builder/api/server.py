"""Command-line entry point for the local UDB API server."""

from __future__ import annotations

import argparse
import logging


def main() -> None:
    """Run the FastAPI server on loopback unless the user explicitly overrides it."""
    parser = argparse.ArgumentParser(
        description="Run the local Universal Dataset Builder API."
    )
    parser.add_argument("--host", choices=("127.0.0.1", "localhost", "::1"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=17891)
    parser.add_argument(
        "--log-level",
        choices=("critical", "error", "warning", "info", "debug"),
        default="info",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    import uvicorn

    uvicorn.run(
        "universal_dataset_builder.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
