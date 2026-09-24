# Performance and optimization

The generator writes bounded PyArrow batches and compressed Parquet, so medium/large profiles do not require all events in memory. Warehouse loads scan record batches. Greenplum facts use append-optimized column storage, zstd compression, `user_id` distribution, and monthly time partitions.

The executed optimization case is under `benchmarks/greenplum`:

- Before: scan a 3,000,000-row heap distributed randomly and aggregate raw events.
- Problem: full-table scan plus a Redistribute Motion before the final aggregation.
- After: prune to one monthly partition, read the user/day serving layer, and aggregate on the `user_id` distribution key.
- Evidence: exact setup/query SQL and plan excerpts are preserved in the result report.

Five warm-cache runs measured a median **107.077 ms before** and **10.908 ms
after**, a **9.82×** improvement. Environment, caveats, plans, and individual
runs are recorded in
[`greenplum_query_optimization.md`](../benchmarks/results/greenplum_query_optimization.md).
Generator benchmarks remain available via `make benchmark`.
