# Pricing Experiment

## Problem
Higher price can reduce conversion while increasing revenue per payer.

## Business question
Does new pricing increase contribution revenue per assigned visitor at acceptable conversion and refund guardrails?

## Data used
Pricing assignments, checkout/payment events, subscriptions and refunds.

## Analysis approach
Intent-to-treat conversion, ARPPU and revenue-per-assigned-user; bootstrap the skewed revenue metric and segment without selecting a winner post hoc.

## Findings
Not precomputed. Generator fact: new pricing reduces checkout probability and raises prices/Pro propensity.

## Statistical uncertainty
Report bootstrap CI and power; adjust secondary comparisons for multiplicity.

## Proposed decision
Consider staged rollout only if revenue-per-user uplift is robust and conversion/refund guardrails are within pre-agreed limits.

## Risks
Short test horizon misses churn; country mix can still distort comparisons even though revenue is normalized to USD with synthetic daily FX.

## Success metric
Contribution revenue per assigned user, with paid conversion and refund rate as guardrails.

## Measurement plan
Track 90-day cohort LTV after experiment and retain local-currency fields as a reconciliation trail for the USD metric.
