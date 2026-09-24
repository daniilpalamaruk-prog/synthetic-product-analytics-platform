from __future__ import annotations

from datetime import timedelta

CHANNELS = ["organic", "google_ads", "meta_ads", "tiktok", "youtube", "referral", "partners"]
DEVICES = ["web", "ios", "android"]
COUNTRIES = ["US", "GB", "DE", "BR", "IN", "CA"]
COUNTRY_META = {
    "US": ("NA", "en", "USD"), "GB": ("Europe", "en", "GBP"),
    "DE": ("Europe", "de", "EUR"), "BR": ("LATAM", "pt", "BRL"),
    "IN": ("APAC", "en", "INR"), "CA": ("NA", "en", "CAD"),
}
EVENT_NAMES = [
    "ad_impression", "ad_click", "signup", "onboarding_started",
    "onboarding_step_completed", "onboarding_completed", "login", "feature_viewed",
    "feature_used", "trial_started", "checkout_started", "payment_attempted",
    "payment_success", "payment_failed", "subscription_started", "subscription_renewed",
    "subscription_cancelled", "refund_requested", "refund_completed",
    "notification_disabled",
]
FEATURES = [
    ("dashboard", "core", "free", 0), ("task_manager", "core", "free", 0),
    ("calendar", "core", "free", 0), ("collaboration", "engagement", "basic", 31),
    ("automation", "power", "pro", 75), ("analytics", "power", "pro", 120),
    ("notifications", "engagement", "free", 300),
]
CHANNEL = {
    "organic":    dict(quality=0.52, activation=0.12, retention=0.16, paid=0.00, pro=0.00, cpc=0.05),
    "google_ads": dict(quality=0.16, activation=0.02, retention=0.03, paid=0.03, pro=0.01, cpc=2.80),
    "meta_ads":   dict(quality=0.00, activation=0.00, retention=0.00, paid=0.00, pro=0.00, cpc=1.65),
    "tiktok":     dict(quality=-0.58, activation=-0.08, retention=-0.18, paid=-0.04, pro=-0.03, cpc=0.72),
    "youtube":    dict(quality=0.10, activation=0.01, retention=0.03, paid=0.00, pro=0.00, cpc=1.20),
    "referral":   dict(quality=0.70, activation=0.16, retention=0.20, paid=0.06, pro=0.12, cpc=0.20),
    "partners":   dict(quality=0.22, activation=0.04, retention=0.05, paid=0.02, pro=0.04, cpc=1.00),
}


def experiments(start, windows=None):
    windows = windows or {}
    onboarding = windows.get("onboarding", {"start_day": 151, "end_day": 210})
    pricing = windows.get("pricing", {"start_day": 273, "end_day": 321})
    notifications = windows.get("notifications", {"start_day": 304, "end_day": 364})
    return [
        {"experiment_id": "exp_onboarding_v2", "experiment_name": "Onboarding redesign",
         "started_at": start + timedelta(days=int(onboarding["start_day"])), "ended_at": start + timedelta(days=int(onboarding["end_day"])),
         "primary_metric": "onboarding_completion_rate", "status": "completed"},
        {"experiment_id": "exp_pricing_v2", "experiment_name": "Pricing page",
         "started_at": start + timedelta(days=int(pricing["start_day"])), "ended_at": start + timedelta(days=int(pricing["end_day"])),
         "primary_metric": "revenue_per_visitor", "status": "completed"},
        {"experiment_id": "exp_notifications", "experiment_name": "Smart notifications",
         "started_at": start + timedelta(days=int(notifications["start_day"])), "ended_at": start + timedelta(days=int(notifications["end_day"])),
         "primary_metric": "d7_retention", "status": "completed"},
    ]
