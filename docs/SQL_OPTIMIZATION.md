# SQL Optimization Log

No benchmark result is pre-filled. Hardware, ClickHouse version, codecs, cache state and row count must accompany every measurement.

| Query | Dataset/config | Execution before | Rows scanned | Bytes read | Optimization | Execution after | Improvement |
|---|---|---:|---:|---:|---|---:|---:|
| _record measured run_ | | | | | | | |

## Reproducible protocol

1. Generate and load one immutable manifest/seed.
2. Record ClickHouse version, CPU/RAM/storage and table DDL.
3. Run one warm-up, then at least five measured repetitions with query cache disabled or clearly declared.
4. Capture elapsed, `read_rows`, `read_bytes`, `memory_usage` from `system.query_log`.
5. Apply one optimization at a time; compare median and p95, not only best run.

Candidate optimizations: date partition pruning, `PREWHERE`, projection by experiment/cohort, materialized daily rollups, LowCardinality dimensions and ordering aligned to common predicates. Do not claim improvement until `benchmarks/run.py` records it.

