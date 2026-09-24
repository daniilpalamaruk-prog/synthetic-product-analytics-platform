# Contributing

This repository is a synthetic portfolio project. Contributions must not introduce claims about real production usage, business impact or mentoring.

## Workflow

1. Describe the analytical/business question and affected grain.
2. Change YAML configuration before adding new hard-coded business behavior.
3. Update contracts and documentation with schema or metric changes.
4. Generate into a new output directory; never mix runs.
5. Run `python -m pytest -q`, quality validation and pattern analysis.
6. Review with [analytics_review_checklist.md](analytics_review_checklist.md).

## Definition of done

- deterministic behavior for a fixed version/config hash/seed;
- no accidental fanout or broken referential integrity in clean data;
- injected defects confined to raw/quarantine;
- reasonable statistical intervals rather than exact random outcomes;
- no generated large dataset committed to Git;
- facts, measured findings, simulated incidents, synthetic benchmarks and proposed decisions are labeled separately.

## SQL changes

Declare grain, keys, join cardinality, null behavior, timezone and incremental/partition predicate. Include an executable query and do not pre-fill benchmark improvements.

## Experiment changes

Document hypothesis, primary metric, guardrails, allocation, intended MDE, alpha, power and maturity. Report intent-to-treat results and multiplicity handling.

