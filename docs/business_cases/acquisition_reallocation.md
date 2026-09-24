# Acquisition Reallocation

## Problem
Cheap signups may not maximize contribution value.

## Business question
Which channel produces the best mature LTV/CAC, and should budget move?

## Data used
Marketing spend, attributed users, payments, refunds and retention cohorts.

## Analysis approach
Compare CAC, activation, D30, payer conversion, censored LTV and payback by month/channel; use matched maturity windows.

## Findings
Not precomputed. Generator facts favor referral LTV/CAC, give Google higher CAC and stronger value than TikTok, and give TikTok cheap but lower-quality acquisition.

## Statistical uncertainty
Bootstrap user-level LTV; report right-censoring and attribution uncertainty.

## Proposed decision
Test incremental reallocation toward channels with credible marginal contribution, retaining holdouts where feasible.

## Risks
Average channel returns are not marginal returns; scale, auction dynamics and selection bias matter.

## Success metric
Incremental contribution margin and payback at a fixed total acquisition budget.

## Measurement plan
Use geo/time holdouts or randomized budget experiments; review mature cohorts monthly.

