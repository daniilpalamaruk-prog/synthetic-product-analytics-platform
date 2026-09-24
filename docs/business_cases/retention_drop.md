# Retention Drop

## Problem
Aggregate retention can move because product behavior or acquisition mix changed.

## Business question
Which cohort, channel, activation, plan, platform or feature dimension explains the decline?

## Data used
Users, events, experiment assignments, subscriptions and feature catalog.

## Analysis approach
Build exact-day cohort curves, standardize channel mix, decompose composition versus within-segment change and fit an interpretable multivariate model as association analysis.

## Findings
Not precomputed. Generator facts include low-retention TikTok mix growth and a positive month-12 cohort effect.

## Statistical uncertainty
Show cohort denominators/CIs; avoid treating feature adoption association as causal.

## Proposed decision
Choose intervention only after decomposition: acquisition controls for mix shift, product investigation for within-segment degradation.

## Risks
Immature cohorts, survivorship, seasonality and post-treatment feature variables.

## Success metric
Mix-adjusted D30 retention and contribution LTV for mature cohorts.

## Measurement plan
Weekly leading indicators plus monthly matured D30 review with frozen cohort definitions.

