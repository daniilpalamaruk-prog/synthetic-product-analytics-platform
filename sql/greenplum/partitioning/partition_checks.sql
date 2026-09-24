SELECT schemaname, tablename, partitiontablename, partitionboundary
FROM pg_partitions
WHERE schemaname IN ('raw','core')
ORDER BY schemaname, tablename, partitionrank;

-- The plan should scan only monthly partitions intersecting this range.
EXPLAIN SELECT count(*) FROM core.fct_events
WHERE event_date >= date '2025-07-01' AND event_date < date '2025-08-01';
