"""CLI for HAL."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from hal.models import BrowseRequest
from hal.server import browse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hal", description="HAL local agent host")
    sub = parser.add_subparsers(dest="command", required=True)

    browse_cmd = sub.add_parser("browse", help="Browse and extract a webpage")
    browse_cmd.add_argument("url", help="Target URL")
    browse_cmd.add_argument("--mode", choices=["auto", "dom", "vision"], default="auto")
    browse_cmd.add_argument("--json", action="store_true", help="Print full JSON output")
    browse_cmd.add_argument("--out", type=Path, help="Write output JSON to directory")
    return parser


async def _run_browse(args: argparse.Namespace) -> int:
    req = BrowseRequest(url=args.url, mode=args.mode)
    resp = await browse(req)
    data = resp.model_dump(mode="json")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / "hal_output.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved {path}")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"[{data['method_used']}] {data['title']} ({data['confidence']:.2f})")
        print(data["text_markdown"][:2000])
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "browse":
        raise SystemExit(asyncio.run(_run_browse(args)))
