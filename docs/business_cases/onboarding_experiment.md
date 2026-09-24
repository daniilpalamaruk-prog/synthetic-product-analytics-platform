# Onboarding Experiment

## Problem
The local onboarding metric may improve without durable user value.

## Business question
Does treatment improve activation, paid conversion and mature D30 retention?

## Data used
Assignments, events, payments and user registration cohorts.

## Analysis approach
Check sample-ratio mismatch, intent-to-treat conversion uplift, binary confidence intervals, payer revenue bootstrap and mature D30 cohorts.

## Findings
Not precomputed. Generator facts: treatment increases completion/activation and slightly improves first-payment propensity; direct D30 effect is intentionally small.

## Statistical uncertainty
Correct for multiple outcomes and distinguish inconclusive evidence from evidence of no effect.

## Proposed decision
Roll out only if the primary metric is significant, guardrails remain acceptable, and decision-makers accept uncertainty in D30.

## Risks
Novelty effects, underpowered retention, instrumentation mismatch and heterogeneous platform effects.

## Success metric
Activation uplift with non-inferior D30 retention and positive contribution revenue per assigned user.

## Measurement plan
Freeze definitions before analysis; extend follow-up until all included users mature to D30.

