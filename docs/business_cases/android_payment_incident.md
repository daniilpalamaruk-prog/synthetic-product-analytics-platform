# Android Payment Incident (Simulated)

## Problem
A simulated Android-only gateway regression is embedded in version 3.7.0 for 12 days.

## Business question
Did payment conversion fall because of traffic mix, platform release, or checkout demand?

## Data used
Clean events, users, sessions, payments and app_releases; grain: attempt and assigned user.

## Analysis approach
Plot attempt→success by hour/day, platform and version; compare Android with iOS/Web using a difference-in-differences sensitivity check and segment by channel.

## Findings
Not precomputed. Generator fact: success probability is reduced only for the incident window; measured size depends on seed/volume.

## Statistical uncertainty
Report binomial CI, sample sizes and pre-period parallel-trend limitations.

## Proposed decision
If measured evidence matches the embedded incident, pause Android rollout and prioritize gateway fix/failed-payment recovery.

## Risks
Version adoption and acquisition mix can confound an unadjusted before/after comparison.

## Success metric
Android attempt→success returns within the pre-release confidence band without harming other platforms.

## Measurement plan
Monitor hourly for 14 days after fix; pre-register recovery threshold and guardrails.

