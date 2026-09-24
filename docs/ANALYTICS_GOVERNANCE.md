# Analytics Governance

This is a proposed governance model for a synthetic portfolio platform. It does not describe real organizational ownership or mentoring experience.

## Sources of truth

| Domain | Source of truth | Grain |
|---|---|---|
| Registered users and acquisition attributes | `dim_users` / clean `users` | one row per user |
| Acquisition cost and delivery | clean `marketing_spend` | date × channel × campaign × country |
| Currency conversion | clean `fx_rates` | date × currency |
| Product behavior | `fct_events` / clean `events` | one row per valid event |
| Payments and recognized cash events | `fct_payments` / clean `payments` | one row per payment attempt |
| Subscription state | clean `subscriptions` | one row per subscription spell |
| Experiment enrollment | clean `experiment_assignments` | experiment × assigned user |
| Feature eligibility | clean `feature_catalog` | one row per feature |
| Pipeline SLI evidence | clean `pipeline_runs` | one row per logical daily run |

Revenue must not be reconstructed from `payment_success` events when payment rows are available. Cross-country revenue, spend, CAC and LTV use `*_usd`; `*_local` plus `currency` remain the audit trail. Assignment must not be inferred from event properties. Channel CAC combines `users` with `marketing_spend`; attribution assumptions must be disclosed.

## Ownership model

Roles are portfolio design roles, not claims about real employees:

- Analytics owner: approves metric semantics, denominators, exclusions and mart grain.
- Data-contract owner: owns source schemas, accepted values, referential tests and compatibility classification.
- Pipeline owner: owns freshness, completeness, availability, duration and backfill behavior.
- Experiment owner: freezes hypothesis, primary metric, guardrails, assignment population and power assumptions before analysis.

Each metric change requires a named proposed owner in the pull request, affected dashboards/queries, validation evidence and migration date.

## Naming conventions

- `stg_*`: one-to-one typed source projections.
- `int_*`: reusable transformations that are not end-user contracts.
- `dim_*`: descriptive entity at a declared stable grain.
- `fct_*`: immutable or append-oriented facts at a declared grain.
- `mart_*`: consumption models with documented business grain.
- timestamps end in `_at`, dates in `_date`, boolean fields use affirmative names such as `auto_renew`.
- rates use 0–1 numeric representation; currency columns must accompany monetary values.

## Contract changes and compatibility

Additive nullable columns and new enum values are backward-compatible only after downstream impact review. Renames, removals, type narrowing, grain changes and changed metric semantics are breaking changes. Breaking changes require a versioned replacement, dual-run comparison and announced migration window.

Contract PRs must update JSON Schema/dbt tests, generator config, sample data, analytical docs and tests in the same change. Seed reproducibility is scoped to a project version plus configuration hash.

## Deprecation policy

1. Mark the relation/field deprecated and provide its replacement.
2. Keep both definitions for at least one documented migration cycle.
3. Identify repository consumers with code search and run comparison checks.
4. Remove only in a declared breaking release; record the change in release notes.

## Metric governance

`docs/METRICS.md` is the semantic contract. A metric proposal must state definition, numerator, denominator, exclusions, grain, window, timezone, maturity and source-of-truth models. Experimental variants must not silently redefine canonical business metrics.
