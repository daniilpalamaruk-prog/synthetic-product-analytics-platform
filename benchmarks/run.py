#!/usr/bin/env python3
"""Execute baseline SQL and persist measured ClickHouse statistics; never fabricates results."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=8123)
    p.add_argument("--user", default="default")
    p.add_argument("--password", default="")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--query", choices=["funnel", "retention", "revenue", "feature_adoption", "ab_aggregation"])
    p.add_argument("--output", type=Path, default=Path("benchmark_results/results.json"))
    args = p.parse_args()
    try:
        import clickhouse_connect
    except ImportError as exc:
        raise SystemExit("Install benchmark dependency: pip install clickhouse-connect") from exc
    client = clickhouse_connect.get_client(host=args.host, port=args.port, username=args.user, password=args.password)
    names = [args.query] if args.query else ["funnel", "retention", "revenue", "feature_adoption", "ab_aggregation"]
    results = []
    for name in names:
        sql = (Path(__file__).parent / f"{name}.sql").read_text(encoding="utf-8")
        parameters = {"start": "2025-01-01", "end": "2025-12-31"}
        settings = {"use_query_cache": 0}
        client.query(sql, parameters=parameters, settings=settings)  # warm-up
        elapsed, read_rows, read_bytes = [], [], []
        for _ in range(args.runs):
            t0 = time.perf_counter(); result = client.query(sql, parameters=parameters, settings=settings); elapsed.append(time.perf_counter() - t0)
            summary = getattr(result, "summary", {}) or {}
            read_rows.append(int(summary.get("read_rows", 0)))
            read_bytes.append(int(summary.get("read_bytes", 0)))
        results.append({"query": name, "runs": args.runs, "median_seconds": statistics.median(elapsed),
                        "p95_seconds": sorted(elapsed)[max(0, int(len(elapsed) * .95) - 1)],
                        "median_rows_scanned": statistics.median(read_rows),
                        "median_bytes_read": statistics.median(read_bytes),
                        "result_rows": len(result.result_rows), "samples_seconds": elapsed,
                        "samples_rows_scanned": read_rows, "samples_bytes_read": read_bytes})
    payload = {"measured_at": datetime.now(timezone.utc).isoformat(), "server_version": client.server_version, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__": main()
