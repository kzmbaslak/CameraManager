"""Export the FastAPI OpenAPI contract without starting the server."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAPI sozlesmesini JSON olarak uretir.")
    parser.add_argument(
        "--output",
        type=Path,
        help="JSON cikti yolu. Verilmezse yalnizca endpoint ozeti yazilir.",
    )
    args = parser.parse_args()

    schema = app.openapi()
    paths = schema.get("paths", {})
    route_count = sum(len(methods) for methods in paths.values() if isinstance(methods, dict))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"OpenAPI schema written: {args.output}")
    else:
        print(f"OpenAPI schema ready: {len(paths)} paths, {route_count} operations")


if __name__ == "__main__":
    main()
