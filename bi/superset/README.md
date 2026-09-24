# Superset layer

Superset queries only `marts`, never raw tables. `dashboard_spec.yaml` is the
version-neutral source specification. `bootstrap.py` idempotently registers
the Greenplum connection, six datasets, ten charts, and five dashboards for
the pinned Superset image.

Real headless-browser captures from the running local service are committed
under `docs/images`. Recreate them with
`python scripts/capture_superset.py` after `docker compose --profile full up -d`.
