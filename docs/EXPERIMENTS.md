# Experiments

The existing experiment engine is preserved. Enrollment is mutually exclusive. Reports distinguish primary, secondary, guardrail, and exploratory metrics; run SRM before interpretation; report confidence intervals and p-values; bootstrap revenue per assigned user in USD; and apply Holm only inside the predefined secondary family.

The onboarding D30 effect is isolated from the notification experiment. Pricing is evaluated as a conversion-versus-ARPPU/contribution trade-off, not on one metric. A low p-value is not an automatic decision: practical size, interval width, guardrails, maturity, and power/MDE assumptions remain visible.

Run `python analysis/experiment_analysis.py --input <dataset> --output <report.json>` and the experiment regression tests. Synthetic effects are generator design choices; measured estimates still depend on seed, sample, censoring, and configured scenario.
