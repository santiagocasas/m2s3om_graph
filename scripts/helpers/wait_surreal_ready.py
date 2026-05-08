#!/usr/bin/env python3
import argparse

from m2s3om_graph.db.surreal_health import wait_for_surreal_ready


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wait until SurrealDB accepts sign-in")
    parser.add_argument("--url", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--attempts", type=int, default=45)
    parser.add_argument("--delay", type=float, default=1.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = wait_for_surreal_ready(
        url=args.url,
        username=args.user,
        password=args.password,
        namespace=args.namespace,
        database=args.database,
        attempts=args.attempts,
        delay_seconds=args.delay,
    )
    if result.ready:
        print("SurrealDB is ready")
        return 0
    print(f"SurrealDB readiness check failed: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
