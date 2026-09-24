# Greenplum / MPP design

Greenplum is an optional real local profile, not a README-only label. `compose.yaml` pins a single-node GPDB 7.1.0 learning image and initializes SQL from `sql/greenplum/ddl`. SQLite remains the default CI fallback.

## Distribution

Large user-centered facts (`events`, `payments`, `subscriptions`) use `DISTRIBUTED BY (user_id)`. This colocates their dominant joins with `dim_users` and with each other, avoiding Motion/redistribution for common user analysis. Small stable dimensions (`dim_plans`, `dim_campaigns`, `dim_date`) are replicated so every segment can join locally.

Risks: a small number of extremely active users can skew facts; nullable or sequential keys can concentrate data; joining on a different key still causes Motion. Run `distribution/skew_diagnostics.sql` and investigate a high max-to-average row ratio plus Motion nodes in `EXPLAIN`.

## Partitioning

Events partition monthly by `event_date`; payments partition monthly by `payment_at`. Monthly grain gives useful pruning for daily/monthly analysis without creating thousands of tiny partitions. Half-open predicates on these columns enable pruning. Partition bounds in the portfolio DDL cover 2025–2026 and must be extended before generating outside that horizon.

## Local run and caveats

Copy `.env.example` to an untracked `.env`, set secrets, then run `make greenplum-up` and connect on port 5433. The image is a third-party development convenience; evaluate and pin an approved image/build in a real organization. A single-node container demonstrates GP syntax and plans but not multi-host failure behavior or realistic network redistribution cost.
