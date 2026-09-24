# Apache Superset

The BI layer runs in the `bi`/`full` Compose profiles and queries only
`marts`. `bi/superset/dashboard_spec.yaml` defines five groups:

1. Executive: revenue, daily active users, and LTV/CAC.
2. Retention: cohort-month/channel table with D1/D7/D30/D90 checkpoints.
3. Acquisition: registrations, CAC, observed contribution LTV, and LTV/CAC by channel.
4. Experiments: checkout and payment conversion by variant; formal uncertainty remains in the JSON experiment report.
5. Incident: payment success by time/platform/version, exposing Android 3.7.0.

`bootstrap.py` idempotently provisions the Greenplum connection, six datasets,
ten charts, and five dashboards for Superset 4.1.1. Native export formats can
change between releases, so the YAML specification and Python bootstrap are
the stable source artifacts.

The five genuine screenshots under `docs/images` were captured from the
running service against deterministic synthetic Greenplum marts. Recreate them
with `python scripts/capture_superset.py`.
