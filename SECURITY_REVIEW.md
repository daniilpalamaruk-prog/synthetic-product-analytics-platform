# Security review

Review date: 2026-09-24.

## Scope and method

The repository was scanned recursively for common cloud/API token prefixes, private-key headers, credential assignments, `.env` files, machine-specific paths, and unusually large files. Configuration, Compose, Python, SQL, Markdown, YAML, and generated assets were included; binary Parquet was size-reviewed separately.

## Results

- Credentials/tokens/private keys: none found.
- `.env`: none present. `.gitignore` excludes `.env`/variants while retaining `.env.example`.
- Example secrets: placeholders only; Compose requires runtime passwords/secrets instead of supplying usable defaults.
- PII: generator values are explicitly fake/reserved. Warehouse ETL pseudonymizes contact identifiers, optionally encrypts reversible values, redacts quarantine payloads, and tests marts for forbidden columns.
- RBAC: `security/roles.sql` prevents analyst/BI access to raw schemas. Login credentials are out-of-band.
- Machine paths: none remain in committed configuration; `.env.example` uses a relative dataset path.
- Large/generated files: 16.82 MB under `data/analytics_ready` and 0.76 MB under `sample/fx_release` were removed from the repository workspace. They are reproducible and were moved to a temporary recovery folder during this work rather than irreversibly erased.
- Caches: known Python/pytest caches were removed; ignore rules cover future caches, databases, logs, and generated data.
- Benchmark artifact: the committed JSON is small and contains environment characteristics only, no usernames or paths.

## Residual risks

This synthetic repository does not implement a KMS, automated secret rotation, row-level security, network policy, audit-log retention, vulnerability/image scanning, backups, or incident response. The optional Greenplum container is a pinned third-party development image and must be reviewed before organizational use. Superset/Airflow local administrators are appropriate only for isolated development.

## Publication decision

Ready for public portfolio publication from a source/secret/PII perspective, subject to the documented limitation that Docker services and Greenplum plans were not executed in this environment.
