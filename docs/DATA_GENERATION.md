# Data Generation Architecture

## Assumptions

- The product is a fictional B2C subscription SaaS; all people, incidents and outcomes are synthetic.
- One user has one registration and may have many sessions, events, subscription spells and payments.
- Event timestamps are UTC. Synthetic months contain 30 days for reproducible scenario boundaries.
- Monetary facts retain local amounts and currency, and also contain USD amounts converted with the synthetic daily `fx_rates` table.
- Relationships are causal-like simulation mechanisms, not causal proof.

## Entities and relationships

```text
marketing_spend ──campaign/channel──> users ──1:N──> sessions ──1:N──> events
                                      │                 │
                                      ├─1:N──> subscriptions ──1:N──> payments
                                      └─1:N──> experiment_assignments ──N:1──> experiments
events.feature_name ──N:1──> feature_catalog
events.app_version  ──N:1──> app_releases (platform/version/time-aware)
pipeline_runs describes daily synthetic pipeline operation independently of user facts
fx_rates(date, currency) ──1:N──> payments / marketing_spend monetary conversion
```

## Generation stages

1. Load and hash `generation.yaml`, `business_rules.yaml`, `scenarios.yaml`.
2. Write static catalogs, daily FX rates, experiments, releases, business timeline and marketing spend.
3. Generate deterministic user batches and latent quality.
4. Simulate lifecycle, activation, sessions and retention checkpoints.
5. Simulate subscription spells, renewals, plan transitions, churn and refunds.
6. Apply experiments and temporal Android incident.
7. Write clean facts in bounded Parquet parts.
8. Copy/corrupt controlled raw records and write affected records to quarantine.
9. Generate synthetic daily `pipeline_runs` and monitoring report.
10. Persist manifest with parameters, row counts and configuration hash/snapshot.

Current simulation deliberately enforces **mutually exclusive experiment enrollment**: a user has at most one `(experiment_id, variant)` assignment. The relational contract still uses `(experiment_id, user_id)` as the assignment key so a future version can support overlapping experiments without changing assignment grain.

## Configuration surface

- `generation.yaml`: profiles, volumes, chunking and run defaults.
- `business_rules.yaml`: retention, channel mix/economics, FX bases, prices, churn, experiment metric roles and anomaly rates.
- `scenarios.yaml`: monthly volume, release months, incident timing/effect and SLA thresholds.

CLI arguments override run-level defaults. To create a scenario, copy the config directory, edit YAML and pass `--config-dir`. The entire resolved configuration is embedded in `manifest.json`.

## Scale

User batches are derived from `chunk_size / events_per_user`; events are flushed as independent compressed Parquet parts. Raw/clean copies exist per chunk, but the complete target dataset is never held in memory. Large outputs belong outside Git.
