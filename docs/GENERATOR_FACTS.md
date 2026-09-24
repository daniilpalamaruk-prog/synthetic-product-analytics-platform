# Generator Facts

Документ описывает только заложенные механизмы. Это не analytical findings.

## Temporal story

| Synthetic month | Встроенное изменение |
|---|---|
| 1–2 | baseline |
| 3 | launch TikTok campaign |
| 4 | acquisition volume step-up |
| 5 | onboarding v2 release: +3.5 pp completion propensity before user/cohort variance |
| 6 | onboarding experiment |
| 7 | Android 3.7.0 payment regression |
| 8 | fix after 12 days |
| 9 | pricing-page v2 release: −1 pp checkout propensity before experiment variance |
| 10 | pricing experiment |
| 11 | budget reallocation away from TikTok |
| 12 | positive retention cohort effect |

Месяц — 30 synthetic days от `--start-date`; это сделано для детерминированной симуляции, не календарного биллинга.

## Probabilistic relationships

Каждый user получает latent quality с индивидуальным noise. Channel, device, cohort, experiment и activation модифицируют вероятности, но не устанавливают outcome жёстко. Activity ages sampled from exponential decay. D1/D7/D30/D90 checkpoints создаются Bernoulli trials; текущая реализация не навязывает монотонность retained states.

Финансовые параметры планов и channel CPC заданы в USD. Для каждой даты и валюты генератор создаёт синтетический `rate_to_usd`, записывает локальную сумму и её USD equivalent. Это generator fact и не имитация исторических рыночных FX котировок.

Onboarding v2 release changes later cohorts, then onboarding treatment adds a further completion/activation effect. Its D30 coefficient is intentionally small relative to variance. Pricing-page v2 adds baseline friction from month 9; pricing treatment further reduces checkout probability and raises price/Pro mix. Notification treatment increases D7 propensity and generates `notification_disabled` trade-off events.

Feature generation respects plan eligibility and notification release date. Collaboration is limited to paid plans; automation/analytics to Pro. Advanced adoption is more likely among activated users, while churn probability depends on activation/channel quality and ordinary activity stops after churn. These are causal-like simulation inputs; feature/churn analysis remains observational.

## Controlled defects

При `--inject-data-quality-issues true` raw получает примерно 0.3% duplicate events, 0.2% null user IDs, 0.1% invalid names, 0.1% impossible timestamps, 1.5% late-arrival markers, 0.08% negative payments и 0.2% duplicate payments. Малые выборки имеют дискретное отклонение. Clean остаётся исходным dataset; affected copies пишутся в quarantine.

## Reproducibility

IDs — deterministic MD5-derived UUID-shaped keys; random sequence — Python `random.Random(seed)`. Совпадают строки и распределения для одинаковой версии, параметров и seed. Part boundaries могут измениться при другом chunk size, не меняя target clean event count.
