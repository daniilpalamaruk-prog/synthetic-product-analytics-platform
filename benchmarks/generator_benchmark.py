#!/usr/bin/env python3
"""Run and record a real generator throughput benchmark (no prefilled numbers)."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saasgen.config import GeneratorConfig
from saasgen.generator import generate
from saasgen.settings import load_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=20_000)
    parser.add_argument("--target-events", type=int, default=1_000_000)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/generator_benchmark"))
    parser.add_argument("--result", type=Path, default=Path("benchmark_results/generator.json"))
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--trace-memory", action="store_true",
                        help="Enable tracemalloc (slows large runs substantially and excludes native PyArrow memory)")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Choose a new --output directory: {args.output} already exists")
    config = GeneratorConfig(args.users, args.target_events, args.seed, args.output,
                             chunk_size=args.chunk_size, inject_data_quality_issues=False,
                             model=load_model(args.config_dir))
    config.validate()
    if args.trace_memory:
        tracemalloc.start()
    started = time.perf_counter(); manifest = generate(config); elapsed = time.perf_counter() - started
    peak = tracemalloc.get_traced_memory()[1] if args.trace_memory else None
    if args.trace_memory:
        tracemalloc.stop()
    output_bytes = sum(p.stat().st_size for p in args.output.rglob("*.parquet"))
    result = {"measured_at": datetime.now(timezone.utc).isoformat(), "synthetic_benchmark": True,
              "environment": {"platform": platform.platform(), "python": sys.version.split()[0],
                              "logical_cpu_count": os.cpu_count()},
              "parameters": manifest["parameters"], "elapsed_seconds": elapsed,
              "events_per_second": args.target_events / elapsed, "parquet_bytes": output_bytes,
              "python_tracemalloc_peak_bytes": peak,
              "note": "tracemalloc excludes some native PyArrow allocations; measure process RSS externally for capacity planning"}
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
