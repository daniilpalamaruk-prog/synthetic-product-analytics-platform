# Greenplum query optimization benchmark

Run on 2026-09-24 against the repository's real Docker Greenplum 7.1.0
service. This is a reproducible local benchmark, not a production capacity
claim.

## Environment

- Greenplum 7.1.0, 1 coordinator and 2 primary segments
- Docker Engine 29.8.0 / Docker Desktop
- Docker VM allocation: 12 CPUs, 8.0 GB RAM
- source rows: 3,000,000 synthetic events
- preaggregated rows: 600,001 user-day records
- measured query: top 100 users by July 2026 event count and revenue
- five measured warm-cache executions after one warm-up

The setup and exact queries live in
[`benchmarks/greenplum/`](../greenplum/).

## Change

```diff
- heap table
- DISTRIBUTED RANDOMLY
- no date partitioning
- aggregate raw events at dashboard query time
+ append-optimized columnar table with zstd compression
+ DISTRIBUTED BY (user_id), matching the GROUP BY key
+ monthly RANGE partitions on event_date
+ user-day preaggregation for the serving query
```

## Results

| Run | Before, ms | After, ms |
|---:|---:|---:|
| 1 | 123.688 | 12.746 |
| 2 | 107.077 | 10.236 |
| 3 | 110.754 | 11.153 |
| 4 | 105.660 | 10.908 |
| 5 | 103.894 | 10.577 |
| **Median** | **107.077** | **10.908** |

Median execution time improved by **9.82×** (89.8% lower).

## Plan evidence

The baseline plan performed a sequential scan of the full unpartitioned
table and then redistributed partial aggregates:

```text
Seq Scan on benchmark.events_unoptimized
Rows Removed by Filter: 1422450  (per segment)
Redistribute Motion 2:2
Execution Time: 110.808 ms
```

The optimized plan scanned one monthly partition out of 24 and avoided a
redistribute motion because both the serving table and aggregation use
`user_id`:

```text
Dynamic Seq Scan on benchmark.events_daily_preaggregated
Number of partitions to scan: 1 (out of 24)
HashAggregate (Group Key: user_id)
Execution Time: 10.622 ms
```

The result combines three effects by design: partition pruning, distribution
aligned with the grouping key, and preaggregation. It does not attempt to
attribute the speedup to any one change.

## Reproduce

With the full stack running:

```bash
docker compose cp benchmarks/greenplum/. greenplum:/tmp/greenplum-benchmark
docker compose exec -T -u gpadmin greenplum \
  /usr/local/greenplum-db/bin/psql -v ON_ERROR_STOP=1 \
  -d synthetic_saas -f /tmp/greenplum-benchmark/setup.sql
docker compose exec -T -u gpadmin greenplum \
  /usr/local/greenplum-db/bin/psql -d synthetic_saas \
  -f /tmp/greenplum-benchmark/before.sql
docker compose exec -T -u gpadmin greenplum \
  /usr/local/greenplum-db/bin/psql -d synthetic_saas \
  -f /tmp/greenplum-benchmark/after.sql
```
