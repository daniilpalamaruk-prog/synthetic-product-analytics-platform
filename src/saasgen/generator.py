from __future__ import annotations

import hashlib
import math
import random
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from datetime import time as datetime_time

from .catalog import (
    CHANNEL,
    CHANNELS,
    COUNTRIES,
    COUNTRY_META,
    DEVICES,
    FEATURES,
    experiments,
)
from .config import GeneratorConfig
from .io import DatasetWriter, write_json
from .settings import deep_get, model_hash


def _id(namespace: str, number: int | str) -> str:
    raw = hashlib.md5(f"synthetic-saas:{namespace}:{number}".encode()).hexdigest()
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def _clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def _rule(config: GeneratorConfig, path: str, default):
    return deep_get(config.model, path, default)


def _month_weights(months: int, config: GeneratorConfig) -> list[float]:
    # Temporal story: TikTok launch, acquisition growth, then budget reallocation.
    base = list(_rule(config, "monthly_acquisition_multipliers",
                      [0.75, 0.78, 0.92, 1.35, 1.32, 1.38, 1.40, 1.36, 1.42, 1.45, 1.28, 1.31]))
    return base + [1.30] * max(0, months - 12)


def _channel_weights(month: int, config: GeneratorConfig) -> list[float]:
    growth_start = int(_rule(config, "timeline.tiktok_growth_start_month", 3)) - 1
    reallocation = int(_rule(config, "timeline.budget_reallocation_month", 11)) - 1
    phase = "baseline" if month < growth_start else ("reallocated" if month >= reallocation else "tiktok_growth")
    defaults = {
        "baseline": [0.22, 0.24, 0.20, 0.01, 0.12, 0.12, 0.09],
        "tiktok_growth": [0.13, 0.18, 0.16, 0.32, 0.08, 0.07, 0.06],
        "reallocated": [0.22, 0.22, 0.13, 0.10, 0.08, 0.16, 0.09],
    }
    configured = _rule(config, f"channel_mix.{phase}", None)
    return [float(configured[c]) for c in CHANNELS] if configured else defaults[phase]


def _channel_effect(config: GeneratorConfig, channel: str) -> dict:
    return dict(CHANNEL[channel]) | dict(_rule(config, f"channels.{channel}", {}))


def _onboarding_d30_effect(profile: dict, config: GeneratorConfig) -> float:
    is_onboarding_treatment = (profile.get("experiment_id") == "exp_onboarding_v2"
                               and profile.get("variant") == "treatment")
    return float(_rule(config, "experiments.onboarding.d30_effect", 0.018)) * is_onboarding_treatment


def _fx_rate(currency: str, when, config: GeneratorConfig) -> float:
    """Synthetic local-currency units to USD for a given UTC date."""
    if isinstance(when, datetime):
        when = when.date()
    base = float(_rule(config, f"fx_rates.base_to_usd.{currency}", 1.0))
    if currency == "USD":
        return 1.0
    day = (when - config.start_date.date()).days
    phase = {"GBP": 0.2, "EUR": 0.8, "BRL": 1.4, "INR": 2.0, "CAD": 2.6}.get(currency, 0.0)
    amplitude = float(_rule(config, "fx_rates.seasonal_amplitude", 0.015))
    return round(base * (1 + amplitude * math.sin(day / 29 + phase)), 8)


def _app_version(device: str, when: datetime, start: datetime, config: GeneratorConfig) -> str:
    month = max(0, (when.year - start.year) * 12 + when.month - start.month)
    if device == "web": return f"web-{25 + month // 2}.0"
    if device == "ios": return f"5.{min(month, 9)}.0"
    if month < 6: return f"3.{month}.0"
    incident_start = start + timedelta(days=int(_rule(config, "android_incident.start_day", 181)))
    fix = incident_start + timedelta(days=int(_rule(config, "android_incident.duration_days", 12)))
    if incident_start <= when < fix: return str(_rule(config, "android_incident.affected_version", "3.7.0"))
    if when >= fix: return str(_rule(config, "android_incident.fixed_version", "3.8.1"))
    return "3.6.0"


def _experiment_for(registration: datetime, end: datetime, rng: random.Random, config: GeneratorConfig):
    candidates = [e for e in experiments(config.start_date, _rule(config, "experiment_windows", {}))
                  if e["started_at"] <= registration <= e["ended_at"]]
    if not candidates:
        return None, None
    exp = rng.choice(candidates)
    variants = ["control", "treatment"] if exp["experiment_id"] != "exp_pricing_v2" else ["control", "new_pricing"]
    return exp["experiment_id"], rng.choice(variants)


def _static_tables(config: GeneratorConfig, writer: DatasetWriter) -> None:
    start, end = config.start_date, config.start_date + timedelta(days=30 * config.months)
    generator_config = [{"config_id": "default", "gross_margin": config.gross_margin,
                         "seed": config.seed, "period_start": start, "period_end": end,
                         "currency_policy": "local_and_usd_at_daily_synthetic_fx",
                         "model_config_hash": model_hash(config.model)}]
    writer.write("raw", "generator_config", generator_config)
    writer.write("clean", "generator_config", generator_config)
    onboarding_month = int(_rule(config, "timeline.onboarding_release_month", 5))
    pricing_month = int(_rule(config, "timeline.pricing_page_release_month", 9))
    reallocation_month = int(_rule(config, "timeline.budget_reallocation_month", 11))
    retention_month = int(_rule(config, "timeline.retention_improvement_month", 12))
    story = [
        (1, "baseline", "Baseline product and channel mix"),
        (2, "baseline_continues", "Baseline period continues"),
        (3, "tiktok_launch", "TikTok campaign starts"),
        (4, "acquisition_growth", "Paid acquisition volume increases"),
        (onboarding_month, "onboarding_v2_release", "New onboarding adds a cohort-level completion uplift"),
        (6, "onboarding_experiment", "Onboarding control versus treatment begins"),
        (7, "android_payment_incident", "Android 3.7.0 payment regression"),
        (8, "android_payment_fix", "Android gateway fix after 12 days"),
        (pricing_month, "pricing_page_v2_release", "New pricing-page experience changes checkout friction"),
        (10, "pricing_experiment", "Control versus new pricing begins"),
        (reallocation_month, "budget_reallocation", "Spend mix moves away from TikTok"),
        (retention_month, "retention_changes", "Retention-focused cohort improvement"),
    ]
    timeline = [{"story_month": month, "effective_at": start + timedelta(days=30 * (month - 1)),
                 "story_event": event, "description": description, "simulated": True}
                for month, event, description in story]
    writer.write("raw", "business_timeline", timeline)
    writer.write("clean", "business_timeline", timeline)
    currencies = sorted({meta[2] for meta in COUNTRY_META.values()})
    fx_rates = [{"date": (start + timedelta(days=day)).date(), "currency": currency,
                 "rate_to_usd": _fx_rate(currency, (start + timedelta(days=day)).date(), config),
                 "source": "synthetic_config", "simulated": True}
                for day in range(config.months * 30 + 1) for currency in currencies]
    writer.write("raw", "fx_rates", fx_rates)
    writer.write("clean", "fx_rates", fx_rates)
    exps = experiments(start, _rule(config, "experiment_windows", {}))
    writer.write("raw", "experiments", exps)
    writer.write("clean", "experiments", exps)
    features = [{"feature_name": n, "category": c, "available_on_plan": p,
                 "release_date": start + timedelta(days=d)} for n, c, p, d in FEATURES]
    writer.write("raw", "feature_catalog", features)
    writer.write("clean", "feature_catalog", features)
    releases = []
    for platform in DEVICES:
        for month in range(config.months):
            released = start + timedelta(days=30 * month + 2)
            releases.append({"app_version": _app_version(platform, released, start, config), "platform": platform,
                             "released_at": released, "description": "Regular synthetic release"})
    incident_day = int(_rule(config, "android_incident.start_day", 181))
    incident_duration = int(_rule(config, "android_incident.duration_days", 12))
    affected_version = str(_rule(config, "android_incident.affected_version", "3.7.0"))
    fixed_version = str(_rule(config, "android_incident.fixed_version", "3.8.1"))
    releases.append({"app_version": affected_version, "platform": "android", "released_at": start + timedelta(days=incident_day),
                     "description": "Simulated payment gateway regression"})
    releases.append({"app_version": fixed_version, "platform": "android", "released_at": start + timedelta(days=incident_day + incident_duration),
                     "description": "Simulated payment gateway fix"})
    writer.write("raw", "app_releases", releases)
    writer.write("clean", "app_releases", releases)

    rng = random.Random(config.seed + 9001)
    spend = []
    for day in range(config.months * 30):
        date = (start + timedelta(days=day)).date()
        month = day // 30
        for channel, share in zip(CHANNELS, _channel_weights(month, config)):
            for country in COUNTRIES:
                currency = COUNTRY_META[country][2]
                fx_rate = _fx_rate(currency, date, config)
                if channel == "organic":
                    impressions, clicks, spend_usd = 0, 0, 0.0
                else:
                    scale = _month_weights(config.months, config)[month] * share * (1 + 0.10 * math.sin(day / 7))
                    clicks = max(1, int(120 * scale * rng.lognormvariate(0, 0.12)))
                    impressions = int(clicks / rng.uniform(0.018, 0.045))
                    spend_usd = round(clicks * _channel_effect(config, channel)["cpc"] * rng.uniform(0.90, 1.10), 2)
                signups = int(clicks * rng.uniform(0.11, 0.23)) if clicks else int(3 * share)
                spend_local = round(spend_usd / fx_rate, 2)
                spend.append({"date": date, "channel": channel, "campaign_id": f"{channel}_{month + 1:02d}",
                              "country": country, "currency": currency, "impressions": impressions, "clicks": clicks,
                              "spend": spend_local, "spend_local": spend_local, "fx_rate_to_usd": fx_rate,
                              "spend_usd": spend_usd, "attributed_signups": signups})
    writer.write("raw", "marketing_spend", spend)
    writer.write("clean", "marketing_spend", spend)


def _profile(i: int, config: GeneratorConfig, rng: random.Random) -> dict:
    month = rng.choices(range(config.months), weights=_month_weights(config.months, config))[0]
    max_day = min(29, (config.start_date + timedelta(days=config.months * 30) - config.start_date).days - month * 30 - 1)
    reg = config.start_date + timedelta(days=month * 30 + rng.randint(0, max_day), seconds=rng.randint(0, 86399))
    channel = rng.choices(CHANNELS, weights=_channel_weights(month, config))[0]
    platform_mix = _rule(config, "platform_distribution", None)
    device = rng.choices(DEVICES, [float(platform_mix[d]) for d in DEVICES] if platform_mix else [0.42, 0.27, 0.31])[0]
    os_name = {"web": rng.choice(["Windows", "macOS", "Linux"]), "ios": "iOS", "android": "Android"}[device]
    country = rng.choices(COUNTRIES, [0.35, 0.12, 0.13, 0.12, 0.18, 0.10])[0]
    region, language, currency = COUNTRY_META[country]
    quality = rng.normalvariate(0, 0.62) + _channel_effect(config, channel)["quality"]
    experiment_id, variant = _experiment_for(reg, reg + timedelta(days=30), rng, config)
    return dict(i=i, user_id=_id("user", i), registration_at=reg, registration_date=reg.date(),
                country=country, region=region, language=language, currency=currency, device_type=device,
                os=os_name, acquisition_channel=channel, campaign_id=f"{channel}_{month + 1:02d}",
                referral_source=("user_referral" if channel == "referral" else None), age_group=rng.choices(
                    ["18-24", "25-34", "35-44", "45-54", "55+"], [0.17, 0.36, 0.25, 0.14, 0.08])[0],
                quality=quality, month=month, experiment_id=experiment_id, variant=variant)


def _make_user(profile: dict) -> dict:
    return {k: profile[k] for k in ["user_id", "registration_at", "country", "region", "device_type", "os",
            "acquisition_channel", "campaign_id", "referral_source", "age_group", "language", "registration_date"]} | {
            "initial_plan": "free", "first_session_id": _id("session", f"{profile['i']}:0"),
            # Reserved example domains/ranges make the synthetic nature unambiguous.
            "name": f"Synthetic User {profile['i']:07d}",
            "email": f"synthetic.user.{profile['i']:07d}@example.test",
            "phone": f"+1-555-{profile['i'] % 10_000:04d}",
            "ip_address": f"192.0.2.{profile['i'] % 254 + 1}"}


def _simulate_user(profile: dict, budget: int, config: GeneratorConfig, rng: random.Random):
    p, reg = profile, profile["registration_at"]
    calendar_start = datetime.combine(reg.date(), datetime_time.min, tzinfo=reg.tzinfo)
    channel_effect = _channel_effect(config, p["acquisition_channel"])
    onboarding_treatment = p["experiment_id"] == "exp_onboarding_v2" and p["variant"] == "treatment"
    notification_treatment = p["experiment_id"] == "exp_notifications" and p["variant"] == "treatment"
    onboarding_release = p["month"] >= int(_rule(config, "timeline.onboarding_release_month", 5)) - 1
    pricing_page_release = p["month"] >= int(_rule(config, "timeline.pricing_page_release_month", 9)) - 1
    completed = rng.random() < _clamp(
        float(_rule(config, "activation.onboarding_base", 0.62)) + channel_effect["activation"]
        + float(_rule(config, "activation.onboarding_release_effect", 0.035)) * onboarding_release
        + float(_rule(config, "experiments.onboarding.completion_effect", 0.085)) * onboarding_treatment
        + float(_rule(config, "activation.quality_effect", 0.08)) * p["quality"])
    core_count = sum(rng.random() < _clamp(
        float(_rule(config, "activation.core_feature_base", 0.38))
        + float(_rule(config, "activation.core_feature_quality_effect", 0.13)) * p["quality"]
        + float(_rule(config, "experiments.onboarding.core_feature_effect", 0.07)) * onboarding_treatment) for _ in range(3))
    activated = completed and core_count >= 2
    pricing_treatment = p["experiment_id"] == "exp_pricing_v2" and p["variant"] == "new_pricing"
    checkout = rng.random() < _clamp(0.20 + float(_rule(config, "activation.activated_paid_effect", 0.035)) * activated
                                     + channel_effect["paid"] - 0.010 * pricing_page_release
                                     + float(_rule(config, "experiments.pricing.checkout_effect", -0.025)) * pricing_treatment)
    incident_start = config.start_date + timedelta(days=int(_rule(config, "android_incident.start_day", 181)))
    incident_end = incident_start + timedelta(days=int(_rule(config, "android_incident.duration_days", 12)))
    incident = p["device_type"] == "android" and incident_start <= reg < incident_end
    success_prob = (float(_rule(config, "android_incident.normal_payment_success", 0.70)) if not incident
                    else float(_rule(config, "android_incident.incident_payment_success", 0.30)))
    paid = checkout and rng.random() < success_prob
    pro_prob = _clamp(float(_rule(config, "plans.base_pro_probability", 0.28)) + channel_effect["pro"]
                      + float(_rule(config, "experiments.pricing.pro_effect", 0.08)) * pricing_treatment)
    plan = "pro" if paid and rng.random() < pro_prob else ("basic" if paid else "free")
    price_usd = ((float(_rule(config, "plans.new_pricing_pro_price", 39.0)) if pricing_treatment
              else float(_rule(config, "plans.pro_price", 35.0))) if plan == "pro" else
             ((float(_rule(config, "plans.new_pricing_basic_price", 17.0)) if pricing_treatment
               else float(_rule(config, "plans.basic_price", 15.0))) if plan == "basic" else 0.0))
    if paid:
        months_alive = min(8, max(1, int(rng.expovariate(1 / (
            float(_rule(config, "churn.mean_months_base", 3.5))
            + float(_rule(config, "churn.mean_months_activated_effect", 2.0)) * activated + p["quality"])))))
        churn_prob = _clamp(float(_rule(config, "churn.base_probability", 0.25)) - channel_effect["retention"]
                            - float(_rule(config, "churn.activated_reduction", 0.07)) * activated)
        churned = rng.random() < churn_prob
        ended = reg + timedelta(days=30 * months_alive) if churned else None
        periods = min(months_alive, max(1, (config.months * 30 - (reg - config.start_date).days) // 30))
        refund_period = (rng.randrange(periods) if periods and
                         rng.random() < float(_rule(config, "payments.refund_probability", 0.025)) else None)
    else:
        months_alive = periods = 0; churned = False; ended = refund_period = None

    retain_base = (float(_rule(config, "retention.d30_base", 0.095)) + channel_effect["retention"]
                   + float(_rule(config, "retention.activated_d30_effect", 0.225)) * activated
                   + float(_rule(config, "retention.paid_d30_effect", 0.045)) * paid)
    degrading_months = set(_rule(config, "cohort_effects.degrading_zero_based_months", [3, 6]))
    retention_release = int(_rule(config, "timeline.retention_improvement_month", 12)) - 1
    cohort_effect = (float(_rule(config, "cohort_effects.degrading_effect", -0.025))
                     if p["month"] in degrading_months else
                     (float(_rule(config, "cohort_effects.retention_release_effect", 0.025))
                      if p["month"] >= retention_release else 0.0))
    d1 = rng.random() < _clamp(float(_rule(config, "retention.d1_base", 0.43))
                               + float(_rule(config, "retention.activated_d1_effect", 0.08)) * activated + 0.03 * p["quality"])
    d7 = rng.random() < _clamp(float(_rule(config, "retention.d7_base", 0.22))
                               + float(_rule(config, "retention.activated_d7_effect", 0.10)) * activated
                               + channel_effect["retention"] * 0.35 + cohort_effect
                               + float(_rule(config, "experiments.notifications.d7_effect", 0.055)) * notification_treatment)
    d30 = rng.random() < _clamp(retain_base + cohort_effect + _onboarding_d30_effect(p, config))
    d90 = rng.random() < _clamp(float(_rule(config, "retention.d90_base", 0.065))
                                + float(_rule(config, "retention.activated_d90_effect", 0.07)) * activated
                                + channel_effect["retention"] * 0.20 + cohort_effect)

    timeline: list[tuple[datetime, str, str | None, dict]] = []
    def add(seconds, name, feature=None, props=None):
        when = reg + timedelta(seconds=seconds)
        # Lifecycle events belong to the signup session even for late-night registrations.
        if 0 <= seconds < 86400 and when.date() > reg.date():
            when = calendar_start + timedelta(hours=23, minutes=59, seconds=59)
        timeline.append((when, name, feature, props or {}))
    if p["acquisition_channel"] not in {"organic", "referral"}:
        add(-rng.randint(300, 7200), "ad_impression")
        add(-rng.randint(30, 240), "ad_click")
    add(0, "signup", props={"onboarding_experience": "v2" if onboarding_release else "v1",
                             "pricing_page_experience": "v2" if pricing_page_release else "v1"})
    add(30, "onboarding_started")
    if completed:
        for step in range(1, 4): add(60 * step, "onboarding_step_completed", props={"step": step})
        add(260, "onboarding_completed")
    for ix, feature in enumerate(["dashboard", "task_manager", "calendar"][:core_count]):
        add(500 + ix * 1800, "feature_used", feature, {"activation_window": True})
    if checkout:
        add(2400, "trial_started")
        add(3000, "checkout_started")
        add(3060, "payment_attempted")
        add(3120, "payment_success" if paid else "payment_failed", props={"incident": incident})
        if paid: add(3180, "subscription_started")
    if paid:
        for period in range(1, periods):
            timeline.append((calendar_start + timedelta(days=30 * period, hours=1),
                             "subscription_renewed", None, {"billing_period_number": period + 1}))
        if refund_period is not None:
            refund_day = 30 * refund_period + 2
            timeline.append((calendar_start + timedelta(days=refund_day, hours=2), "refund_requested", None, {}))
            timeline.append((calendar_start + timedelta(days=refund_day + 1, hours=2), "refund_completed", None, {}))
        if churned and 30 * months_alive <= max(1, config.months * 30 - (reg - config.start_date).days):
            timeline.append((calendar_start + timedelta(days=30 * months_alive), "subscription_cancelled", None, {}))
    checkpoints = [(1, d1), (7, d7), (30, d30), (90, d90)]
    for day, retained in checkpoints:
        if churned and day > 30 * months_alive:
            continue
        if retained and reg + timedelta(days=day) < config.start_date + timedelta(days=config.months * 30):
            timeline.append((calendar_start + timedelta(days=day, seconds=rng.randint(0, 3600)),
                             "login", None, {"retention_day": day}))
            timeline.append((calendar_start + timedelta(days=day, seconds=rng.randint(3700, 7200)),
                             "feature_used", rng.choice([f[0] for f in FEATURES[:4]]), {}))
    if notification_treatment and rng.random() < float(_rule(config, "experiments.notifications.disable_probability", 0.19)):
        timeline.append((calendar_start + timedelta(days=5, seconds=rng.randint(0, 7200)),
                         "notification_disabled", "notifications",
                         {"reason": rng.choice(["too_frequent", "irrelevant", "privacy"])}))

    # Fill volume inside a limited set of active days. Reusing days is essential:
    # event density must not mechanically turn exact-day retention into ~100%.
    max_age = max(1, (config.start_date + timedelta(days=config.months * 30) - reg).days)
    if churned:
        max_age = min(max_age, 30 * months_alive)
    checkpoint_state = {1: d1, 7: d7, 30: d30, 90: d90}
    active_day_pool = {0}
    desired_days = max(2, min(18, int(3 + math.log1p(budget) * (0.8 + 0.35 * activated + 0.15 * paid))))
    attempts = 0
    while len(active_day_pool) < desired_days and attempts < desired_days * 20:
        attempts += 1
        scale = 13 + 16 * activated + 8 * paid + max(0, 4 * p["quality"])
        day = min(max_age, int(rng.expovariate(1 / max(2, scale))))
        if day not in checkpoint_state or checkpoint_state[day]:
            active_day_pool.add(day)
    for day, retained in checkpoint_state.items():
        if retained and day <= max_age:
            active_day_pool.add(day)
    active_day_pool = sorted(active_day_pool)
    while len(timeline) < budget:
        day = rng.choice(active_day_pool)
        when = calendar_start + timedelta(days=day, seconds=rng.randint(600, 85000))
        if day == 0 and when < reg:
            when = reg
        feature_names = ["dashboard", "task_manager", "calendar"]
        feature_weights = [25, 22, 18]
        if plan in {"basic", "pro"}:
            feature_names.append("collaboration"); feature_weights.append(
                float(_rule(config, "feature_effects.collaboration_base_weight", 9))
                + float(_rule(config, "feature_effects.collaboration_activation_weight", 7)) * activated)
        if plan == "pro":
            feature_names.extend(["automation", "analytics"]); feature_weights.extend([
                float(_rule(config, "feature_effects.automation_base_weight", 8))
                + float(_rule(config, "feature_effects.automation_activation_weight", 5)) * activated,
                float(_rule(config, "feature_effects.analytics_base_weight", 6))
                + float(_rule(config, "feature_effects.analytics_activation_weight", 4)) * activated])
        if when >= config.start_date + timedelta(days=300):
            feature_names.append("notifications"); feature_weights.append(7)
        feature = rng.choices(feature_names, feature_weights)[0]
        name = rng.choices(["login", "feature_viewed", "feature_used"], [0.22, 0.32, 0.46])[0]
        timeline.append((when, name, feature if name != "login" else None, {}))
    timeline = sorted(timeline, key=lambda x: x[0])[:budget]

    day_to_session, session_by_day, sessions, events = {}, {}, [], []
    for event_no, (when, name, feature, props) in enumerate(timeline):
        day_key = when.date().isoformat()
        if day_key not in day_to_session:
            session_no = len(day_to_session)
            sid = _id("session", f"{p['i']}:{session_no}")
            day_to_session[day_key] = sid
            session = {"session_id": sid, "user_id": p["user_id"], "session_started_at": when,
                       "session_ended_at": when + timedelta(minutes=rng.randint(3, 42)),
                       "device_type": p["device_type"], "os": p["os"],
                       "app_version": _app_version(p["device_type"], when, config.start_date, config),
                       "country": p["country"], "traffic_source": p["acquisition_channel"]}
            session_by_day[day_key] = session
            sessions.append(session)
        else:
            session = session_by_day[day_key]
            session["session_started_at"] = min(session["session_started_at"], when)
            session["session_ended_at"] = max(session["session_ended_at"], when + timedelta(minutes=3))
        events.append({"event_id": _id("event", f"{p['i']}:{event_no}"), "user_id": p["user_id"],
                       "session_id": day_to_session[day_key], "event_time": when, "event_date": when.date(),
                       "event_name": name, "feature_name": feature, "device_type": p["device_type"], "os": p["os"],
                       "app_version": _app_version(p["device_type"], when, config.start_date, config),
                       "experiment_id": p["experiment_id"], "experiment_variant": p["variant"],
                       "properties": props | {"activated": activated}})

    assignments = []
    if p["experiment_id"]:
        assignments.append({"experiment_id": p["experiment_id"], "user_id": p["user_id"],
                            "variant": p["variant"], "assigned_at": reg})
    subscriptions, payments = [], []
    if paid:
        sub_id = _id("subscription", p["i"])
        sub_started_at = reg + timedelta(seconds=3180)
        start_fx_rate = _fx_rate(p["currency"], sub_started_at, config)
        price_local = round(price_usd / start_fx_rate, 2)
        transition_period = (2 if periods >= 3 and
                             rng.random() < float(_rule(config, "payments.plan_transition_probability", 0.18)) else None)
        second_plan = ("pro" if plan == "basic" else "basic") if transition_period is not None else None
        transition_at = reg + timedelta(days=30 * transition_period) if transition_period is not None else None
        subscriptions.append({"subscription_id": sub_id, "user_id": p["user_id"], "plan": plan,
                              "started_at": sub_started_at, "ended_at": ended,
                              "monthly_price": price_local, "currency": p["currency"],
                              "monthly_price_local": price_local, "monthly_price_usd": price_usd,
                              "billing_period": "monthly",
                              "status": "cancelled" if churned or transition_period is not None else "active",
                              "cancel_reason": ("upgrade" if second_plan == "pro" else "downgrade") if transition_period is not None else
                                               (rng.choice(["too_expensive", "not_using", "missing_feature"]) if churned else None),
                              "auto_renew": not churned and transition_period is None,
                              "acquisition_channel_at_start": p["acquisition_channel"]})
        second_sub_id = None
        second_price_usd = None
        if transition_period is not None:
            subscriptions[-1]["ended_at"] = transition_at
            second_sub_id = _id("subscription_change", p["i"])
            second_price_usd = (float(_rule(config, "plans.pro_price", 35.0)) if second_plan == "pro"
                                else float(_rule(config, "plans.basic_price", 15.0)))
            second_fx_rate = _fx_rate(p["currency"], transition_at, config)
            second_price_local = round(second_price_usd / second_fx_rate, 2)
            subscriptions.append({"subscription_id": second_sub_id, "user_id": p["user_id"], "plan": second_plan,
                                  "started_at": transition_at, "ended_at": ended, "monthly_price": second_price_local,
                                  "currency": p["currency"], "monthly_price_local": second_price_local,
                                  "monthly_price_usd": second_price_usd,
                                  "billing_period": "monthly", "status": "cancelled" if churned else "active",
                                  "cancel_reason": rng.choice(["too_expensive", "not_using"]) if churned else None,
                                  "auto_renew": not churned, "acquisition_channel_at_start": p["acquisition_channel"]})
        for period in range(periods):
            payment_at = reg + timedelta(days=30 * period, seconds=3120)
            failed = period > 0 and rng.random() < float(_rule(config, "payments.renewal_failure_probability", 0.055))
            refunded = not failed and period == refund_period
            effective_sub = second_sub_id if transition_period is not None and period >= transition_period else sub_id
            effective_price_usd = (second_price_usd if transition_period is not None and period >= transition_period
                                   else price_usd)
            fx_rate = _fx_rate(p["currency"], payment_at, config)
            effective_price_local = round(effective_price_usd / fx_rate, 2)
            payments.append({"payment_id": _id("payment", f"{p['i']}:{period}"), "user_id": p["user_id"],
                             "subscription_id": effective_sub, "payment_at": payment_at,
                             "amount": 0.0 if failed else effective_price_local,
                             "amount_local": 0.0 if failed else effective_price_local,
                             "amount_usd": 0.0 if failed else effective_price_usd,
                             "currency": p["currency"], "fx_rate_to_usd": fx_rate,
                             "payment_method": rng.choice(["card", "paypal", "apple_pay", "google_pay"]),
                             "status": "failed" if failed else ("refunded" if refunded else "success"),
                             "failure_reason": rng.choice(["gateway_error", "insufficient_funds", "expired_card"]) if failed else None,
                             "refund_amount": effective_price_local if refunded else 0.0,
                             "refund_amount_local": effective_price_local if refunded else 0.0,
                             "refund_amount_usd": effective_price_usd if refunded else 0.0,
                             "refund_at": payment_at + timedelta(days=rng.randint(1, 10)) if refunded else None})
    return sessions, events, subscriptions, payments, assignments, activated


def _inject_events(records: list[dict], rng: random.Random, config: GeneratorConfig):
    raw = [r.copy() for r in records]
    quarantine = []
    for row in raw:
        x = rng.random()
        null_rate = float(_rule(config, "anomalies.null_event_user", 0.002))
        invalid_rate = float(_rule(config, "anomalies.invalid_event_name", 0.001))
        time_rate = float(_rule(config, "anomalies.impossible_event_time", 0.001))
        variant_rate = float(_rule(config, "anomalies.invalid_experiment_variant", 0.0005))
        if x < null_rate:
            row["user_id"] = None; quarantine.append(row | {"issue_type": "null_user_id"})
        elif x < null_rate + invalid_rate:
            row["event_name"] = "unknown_event"; quarantine.append(row | {"issue_type": "invalid_event_name"})
        elif x < null_rate + invalid_rate + time_rate:
            row["event_time"] = row["event_time"] - timedelta(days=400); quarantine.append(row | {"issue_type": "impossible_timestamp"})
        elif x < null_rate + invalid_rate + time_rate + variant_rate and row.get("experiment_id"):
            row["experiment_variant"] = "variant_z"; quarantine.append(row | {"issue_type": "invalid_experiment_variant"})
        if rng.random() < float(_rule(config, "anomalies.late_event", 0.015)):
            props = dict(row.get("properties", {})); props["late_arrival_hours"] = 36; row["properties"] = props
    duplicate_rate = float(_rule(config, "anomalies.duplicate_events", 0.003))
    duplicate_count = max(1, int(len(raw) * duplicate_rate)) if duplicate_rate > 0 and raw else 0
    duplicates = [r.copy() for r in rng.sample(raw, min(len(raw), duplicate_count))]
    for r in duplicates: quarantine.append(r | {"issue_type": "duplicate_event_id"})
    return raw + duplicates, quarantine


def _inject_payments(records: list[dict], rng: random.Random, config: GeneratorConfig):
    raw = [r.copy() for r in records]
    quarantine = []
    for row in raw:
        if rng.random() < float(_rule(config, "anomalies.negative_payment", 0.0008)):
            row["amount"] = -abs(row["amount"] or 1.0)
            row["amount_local"] = row["amount"]
            row["amount_usd"] = round(row["amount"] * row["fx_rate_to_usd"], 2)
            quarantine.append(row | {"issue_type": "negative_amount"})
        elif rng.random() < float(_rule(config, "anomalies.missing_subscription", 0.001)):
            row["subscription_id"] = _id("missing_subscription", row["payment_id"])
            quarantine.append(row | {"issue_type": "missing_subscription"})
    if raw:
        duplicates = [r.copy() for r in rng.sample(
            raw, min(len(raw), int(len(raw) * float(_rule(config, "anomalies.duplicate_payment", 0.002)))))]
        for r in duplicates: quarantine.append(r | {"issue_type": "duplicate_payment_id"})
        raw.extend(duplicates)
    return raw, quarantine


def _inject_users(records: list[dict], rng: random.Random, config: GeneratorConfig):
    raw = [r.copy() for r in records]; quarantine = []
    for row in raw:
        if rng.random() < float(_rule(config, "anomalies.unknown_campaign", 0.001)):
            row["campaign_id"] = "unknown_campaign"
            quarantine.append(row | {"issue_type": "unknown_campaign_id"})
    return raw, quarantine


def _inject_subscriptions(records: list[dict], rng: random.Random, config: GeneratorConfig):
    raw = [r.copy() for r in records]; quarantine = []
    for row in raw:
        if rng.random() < float(_rule(config, "anomalies.invalid_subscription_dates", 0.0007)):
            row["ended_at"] = row["started_at"] - timedelta(days=1)
            quarantine.append(row | {"issue_type": "ended_before_started"})
    return raw, quarantine


def _build_pipeline_monitoring(config: GeneratorConfig, daily_counts: Counter) -> tuple[list[dict], dict]:
    """Create deterministic synthetic operational telemetry for the historical pipeline."""
    rng = random.Random(config.seed + 41_337)
    availability_hour = int(_rule(config, "sla.daily_availability_hour_utc", 7))
    freshness_target = int(_rule(config, "sla.freshness_minutes", 60))
    completeness_target = float(_rule(config, "sla.completeness_ratio", 0.99))
    duration_target = int(_rule(config, "sla.max_pipeline_duration_minutes", 45))
    allowed_delay = int(_rule(config, "sla.allowed_delay_minutes", 180))
    runs = []
    for offset in range(config.months * 30):
        logical_date = (config.start_date + timedelta(days=offset)).date()
        actual = int(daily_counts.get(logical_date, 0))
        expected = actual
        if offset == min(129, config.months * 30 - 1) and actual:
            expected = math.ceil(actual / 0.985)  # one declared simulated completeness incident
        completeness = actual / expected if expected else (1.0 if actual == 0 else 0.0)
        deadline = datetime.combine(logical_date + timedelta(days=1), datetime_time(hour=availability_hour), tzinfo=timezone.utc)
        duration_minutes = min(duration_target, max(5, int(rng.normalvariate(28, 7))))
        status = "success"
        if offset == min(199, config.months * 30 - 1):
            duration_minutes = duration_target + 165
            status = "failed_then_recovered"
        started_at = deadline - timedelta(hours=1, minutes=15)
        completed_at = started_at + timedelta(minutes=duration_minutes)
        watermark_lag = min(freshness_target, max(5, int(rng.normalvariate(30, 10))))
        source_watermark = completed_at - timedelta(minutes=watermark_lag)
        delay_minutes = max(0, int((completed_at - deadline).total_seconds() / 60))
        runs.append({"run_id": _id("pipeline_run", logical_date.isoformat()), "logical_date": logical_date,
                     "started_at": started_at, "completed_at": completed_at, "source_watermark": source_watermark,
                     "expected_event_rows": expected, "actual_event_rows": actual,
                     "completeness_ratio": round(completeness, 6), "duration_minutes": duration_minutes,
                     "freshness_minutes": watermark_lag, "delay_minutes": delay_minutes,
                     "available_by_sla": completed_at <= deadline,
                     "partition_present": offset != min(249, config.months * 30 - 1),
                     "status": status, "simulated": True})
    summary = {
        "synthetic": True, "disclosure": "Simulated monitoring output; not evidence of a production SLA.",
        "targets": {"availability_hour_utc": availability_hour, "freshness_minutes": freshness_target,
                    "completeness_ratio": completeness_target, "pipeline_duration_minutes": duration_target,
                    "allowed_delay_minutes": allowed_delay,
                    "pipeline_success_rate": float(_rule(config, "sla.target_success_rate", 0.995))},
        "observed": {"runs": len(runs),
                     "success_rate": sum(r["status"] == "success" for r in runs) / len(runs),
                     "availability_rate": sum(r["available_by_sla"] for r in runs) / len(runs),
                     "freshness_pass_rate": sum(r["freshness_minutes"] <= freshness_target for r in runs) / len(runs),
                     "completeness_pass_rate": sum(r["completeness_ratio"] >= completeness_target for r in runs) / len(runs),
                     "duration_pass_rate": sum(r["duration_minutes"] <= duration_target for r in runs) / len(runs),
                     "max_allowed_delay_minutes_observed": max(r["delay_minutes"] for r in runs),
                     "missing_partitions": sum(not r["partition_present"] for r in runs)},
    }
    return runs, summary


def generate(config: GeneratorConfig) -> dict:
    started = time.time()
    if (config.output / "raw").exists() or (config.output / "clean").exists():
        raise FileExistsError(
            f"Output already contains a dataset: {config.output}. Choose a new directory to avoid mixed runs."
        )
    config.output.mkdir(parents=True, exist_ok=True)
    writer = DatasetWriter(config.output, config.csv_sample)
    _static_tables(config, writer)
    rng = random.Random(config.seed)
    ratio = config.target_events / config.users
    user_batch = max(1, min(25_000, int(config.chunk_size / max(4, ratio))))
    base_budget, remainder = divmod(config.target_events, config.users)
    activation = Counter()
    daily_event_counts = Counter()

    for batch_start in range(0, config.users, user_batch):
        users, sessions, events, subscriptions, payments, assignments = [], [], [], [], [], []
        for i in range(batch_start, min(config.users, batch_start + user_batch)):
            profile = _profile(i, config, rng)
            users.append(_make_user(profile))
            budget = base_budget + (1 if i < remainder else 0)
            s, e, sub, pay, assn, active = _simulate_user(profile, budget, config, rng)
            sessions.extend(s); events.extend(e); subscriptions.extend(sub); payments.extend(pay); assignments.extend(assn)
            daily_event_counts.update(row["event_date"] for row in e)
            activation["activated" if active else "not_activated"] += 1
        if config.inject_data_quality_issues:
            raw_events, q_events = _inject_events(events, rng, config)
            raw_payments, q_payments = _inject_payments(payments, rng, config)
            raw_users, q_users = _inject_users(users, rng, config)
            raw_subscriptions, q_subscriptions = _inject_subscriptions(subscriptions, rng, config)
        else:
            raw_events, q_events, raw_payments, q_payments = events, [], payments, []
            raw_users, q_users, raw_subscriptions, q_subscriptions = users, [], subscriptions, []
        for table, raw_rows, clean_rows, q_rows in [
            ("users", raw_users, users, q_users), ("subscriptions", raw_subscriptions, subscriptions, q_subscriptions),
            ("events", raw_events, events, q_events), ("payments", raw_payments, payments, q_payments),
        ]:
            writer.write("raw", table, raw_rows); writer.write("clean", table, clean_rows)
            writer.write("quarantine", table, q_rows)
        for table, rows in [("sessions", sessions), ("experiment_assignments", assignments)]:
            writer.write("raw", table, rows); writer.write("clean", table, rows)

    pipeline_runs, monitoring = _build_pipeline_monitoring(config, daily_event_counts)
    writer.write("raw", "pipeline_runs", pipeline_runs); writer.write("clean", "pipeline_runs", pipeline_runs)
    write_json(config.output / "monitoring_report.json", monitoring)
    period_end = config.start_date + timedelta(days=config.months * 30)
    manifest = {
        "project": "synthetic-saas-analytics", "synthetic": True, "seed": config.seed,
        "model_config_hash": model_hash(config.model), "model_config": config.model,
        "generated_at": datetime.now(timezone.utc), "period_start": config.start_date,
        "period_end": period_end,
        "pipeline": {"logical_run_at": period_end, "source_watermark": period_end - timedelta(minutes=30),
                     "freshness_minutes": 30, "status": "success", "monitoring_summary": monitoring["observed"]},
        "parameters": {"users": config.users, "target_events": config.target_events,
                       "chunk_size": config.chunk_size, "gross_margin": config.gross_margin,
                       "inject_data_quality_issues": config.inject_data_quality_issues},
        "totals": {"users": config.users, "events": config.target_events,
                   "subscriptions": writer.rows.get(("clean", "subscriptions"), 0),
                   "payments": writer.rows.get(("clean", "payments"), 0)},
        "activation_counts": dict(activation), "row_counts": {f"{a}.{b}": n for (a, b), n in writer.rows.items()},
        "elapsed_seconds": round(time.time() - started, 3),
        "disclosure": "All data, incidents, effects and benchmarks in this project are synthetic."
    }
    write_json(config.output / "manifest.json", manifest)
    return manifest
