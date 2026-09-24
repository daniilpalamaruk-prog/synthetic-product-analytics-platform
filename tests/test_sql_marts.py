from pathlib import Path

SQL = Path("sql/marts.sql").read_text(encoding="utf-8").lower()


def test_subscription_mart_is_historical_month_end_snapshot():
    section = SQL.split("create view if not exists synthetic_saas.mart_subscriptions as", 1)[1]
    section = section.split("create view if not exists synthetic_saas.mart_revenue as", 1)[0]
    for field in ("new_mrr_usd", "churned_mrr_usd", "expansion_mrr_usd",
                  "contraction_mrr_usd", "ending_mrr_usd"):
        assert field in section
    assert "started_at < addmonths(m.month_start, 1)" in section
    assert "ended_at >= addmonths(m.month_start, 1)" in section


def test_unit_economics_uses_cumulative_usd_payback_not_twelve_month_proxy():
    section = SQL.split("create view if not exists synthetic_saas.mart_unit_economics as", 1)[1]
    section = section.split("create view if not exists synthetic_saas.mart_experiments as", 1)[0]
    assert "cumulative_contribution_usd" in section
    assert "minif(month_number" in section
    assert "cac_usd" in section
    assert "contribution_ltv / 12" not in section


def test_cross_country_financial_marts_use_usd_fields():
    assert "sum(spend_usd)" in SQL
    assert "amount_usd - p.refund_amount_usd" in SQL
    assert "monthly_price_usd" in SQL
