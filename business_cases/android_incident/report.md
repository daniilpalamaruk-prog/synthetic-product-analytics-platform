# Android payment incident

## Question
Can the payment-success drop be localized to Android version 3.7.0?

## Evidence
| Version | Attempts | Successes | Success rate |
|---|---:|---:|---:|
| 3.0.0 | 39 | 28 | 71.79% |
| 3.1.0 | 37 | 27 | 72.97% |
| 3.2.0 | 43 | 27 | 62.79% |
| 3.3.0 | 55 | 39 | 70.91% |
| 3.4.0 | 63 | 46 | 73.02% |
| 3.5.0 | 75 | 50 | 66.67% |
| 3.7.0 | 31 | 12 | 38.71% |
| 3.8.1 | 318 | 227 | 71.38% |

## Analysis
The fixed-minus-affected success-rate difference is 32.67%.

## Metric impact
The affected metric is payment success per attempt, segmented by platform, version, and time.

## Interpretation
This is a designed synthetic incident; the table is calculated from events rather than hardcoded as a finding.

## Recommendation
Keep 3.7.0 blocked and monitor the fixed release.

## Limitations
Descriptive rates do not isolate gateway, country, retry, or user-mix effects and are not real operational evidence.
