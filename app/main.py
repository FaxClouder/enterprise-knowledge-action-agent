from __future__ import annotations

import argparse
import json

from app.graph import run_query


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(description="Enterprise Knowledge & Action Agent")
    parser.add_argument("query", nargs="?", default="", help="User query")
    parser.add_argument("--user-id", default="demo_user", help="User identifier")
    parser.add_argument("--thread-id", default="demo_thread", help="Thread identifier")
    parser.add_argument("--interactive", action="store_true", help="Interactive session")
    return parser


def run_interactive(user_id: str, thread_id: str) -> None:
    """Run multi-turn interactive CLI."""
    print("Interactive mode. Type 'exit' to quit.")
    while True:
        query = input("\nYou> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        output = run_query(query, user_id=user_id, thread_id=thread_id)
        print("Agent>", json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    """CLI main function."""
    args = build_parser().parse_args()

    if args.interactive:
        run_interactive(user_id=args.user_id, thread_id=args.thread_id)
        return

    if not args.query.strip():
        raise SystemExit("Provide a query or use --interactive")

    output = run_query(args.query, user_id=args.user_id, thread_id=args.thread_id)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
