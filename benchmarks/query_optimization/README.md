# Query optimization benchmark

The before query casts `event_time` in its filter, scans more partitions and joins at event grain. The after query filters the partition key with a half-open range, preaggregates at user/day grain and joins on the common `user_id` distribution key.

This earlier query-design fixture remains useful for external datasets. The
repository's executed, self-contained Docker benchmark is now under
`benchmarks/greenplum`, with measured plans and repeated timings in
`benchmarks/results/greenplum_query_optimization.md`.
