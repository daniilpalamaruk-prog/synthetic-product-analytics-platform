# ETL and ELT

ETL protects user data before it enters the warehouse: validate → normalize email/phone → HMAC identifiers → optional Fernet authenticated encryption → load protected raw. This placement prevents analysts and quarantine payloads from receiving open PII.

ELT handles high-volume product and billing data: Parquet → raw Greenplum/SQLite → SQL staging → core → marts. SQL remains close to the warehouse for partition pruning, colocated joins, and reviewable metric logic.

## Incremental and idempotent behavior

- Source watermarks are half-open UTC intervals.
- Events use `event_time`, payments use `payment_at`, subscriptions use `started_at`, and users use `registration_at`.
- Batch metadata stores ID, timestamps, counts, watermarks, and status.
- SQLite uses primary-key replacement; Greenplum uses anti-joins and interval-scoped mart delete/insert.
- Replaying the same batch preserves fact counts and produces zero duplicates.

Invalid rows go to `quarantine_records` with source, safe identifier, validation error, rejection time, batch ID, and redacted payload. Critical integrity failures stop mart publication; warnings belong in monitoring and do not silently change facts.
