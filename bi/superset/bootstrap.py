"""Idempotently provision the local Greenplum connection and demo dashboards."""

from __future__ import annotations

import json
import os
from urllib.parse import quote_plus

from superset import db
from superset.app import create_app


DATABASE_NAME = "Synthetic SaaS Greenplum"


def sql_metric(label: str, expression: str) -> dict[str, str]:
    return {
        "expressionType": "SQL",
        "sqlExpression": expression,
        "column": None,
        "aggregate": None,
        "datasourceWarning": False,
        "hasCustomLabel": True,
        "label": label,
        "optionName": f"metric_{label.lower().replace(' ', '_')}",
    }


def position_json(charts: list) -> str:
    root = "ROOT_ID"
    grid = "GRID_ID"
    nodes: dict[str, dict] = {
        "DASHBOARD_VERSION_KEY": "v2",
        root: {"id": root, "type": "ROOT", "children": [grid]},
        grid: {"id": grid, "type": "GRID", "children": [], "parents": [root]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": "Synthetic data — portfolio demo"}},
    }
    for index, chart in enumerate(charts, 1):
        row_id = f"ROW-{index}"
        chart_id = f"CHART-{chart.id}"
        nodes[grid]["children"].append(row_id)
        nodes[row_id] = {
            "id": row_id,
            "type": "ROW",
            "children": [chart_id],
            "parents": [root, grid],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        nodes[chart_id] = {
            "id": chart_id,
            "type": "CHART",
            "children": [],
            "parents": [root, grid, row_id],
            "meta": {"chartId": chart.id, "height": 48, "width": 12, "uuid": str(chart.uuid)},
        }
    return json.dumps(nodes)


def main() -> None:
    app = create_app()
    with app.app_context():
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.core import Database
        from superset.models.dashboard import Dashboard
        from superset.models.slice import Slice

        password = quote_plus(os.environ["GREENPLUM_PASSWORD"])
        uri = f"postgresql+psycopg2://gpadmin:{password}@greenplum:5432/synthetic_saas"
        database = db.session.query(Database).filter_by(database_name=DATABASE_NAME).one_or_none()
        if database is None:
            database = Database(database_name=DATABASE_NAME, sqlalchemy_uri=uri, expose_in_sqllab=True)
            db.session.add(database)
        else:
            database.sqlalchemy_uri = uri
            database.expose_in_sqllab = True
        db.session.commit()

        dataset_names = [
            "revenue_daily", "product_daily", "retention_cohort", "experiments",
            "acquisition", "platform_quality",
        ]
        datasets: dict[str, SqlaTable] = {}
        for table_name in dataset_names:
            dataset = (
                db.session.query(SqlaTable)
                .filter_by(database_id=database.id, schema="marts", table_name=table_name)
                .one_or_none()
            )
            if dataset is None:
                dataset = SqlaTable(
                    database_id=database.id,
                    schema="marts",
                    table_name=table_name,
                    main_dttm_col={
                        "revenue_daily": "payment_date",
                        "product_daily": "event_date",
                        "retention_cohort": "cohort_month",
                        "platform_quality": "event_hour",
                    }.get(table_name),
                )
                db.session.add(dataset)
                db.session.flush()
                dataset.fetch_metadata()
            datasets[table_name] = dataset
        db.session.commit()

        chart_specs = [
            ("Executive — Net revenue", "revenue_daily", "echarts_timeseries_line", {
                "x_axis": "payment_date", "metrics": [sql_metric("Net revenue", "SUM(net_revenue_usd)")],
                "y_axis_format": "$,.0f", "show_legend": False,
            }),
            ("Executive — Daily active users", "product_daily", "echarts_area", {
                "x_axis": "event_date", "metrics": [sql_metric("Active users", "SUM(active_users)")],
                "y_axis_format": ",.0f", "show_legend": False,
            }),
            ("Executive — LTV / CAC", "acquisition", "echarts_timeseries_bar", {
                "x_axis": "acquisition_channel", "metrics": [sql_metric("LTV / CAC", "MAX(ltv_cac)")],
                "show_legend": False,
            }),
            ("Retention — Cohort checkpoints", "retention_cohort", "pivot_table_v2", {
                "groupbyRows": ["cohort_month", "acquisition_channel"], "groupbyColumns": ["age_day"],
                "metrics": [sql_metric("Retained users", "SUM(retained_users)")],
                "combineMetric": True, "rowOrder": "key_a_to_z", "colOrder": "key_a_to_z",
            }),
            ("Experiment — Checkout conversion", "experiments", "echarts_timeseries_bar", {
                "x_axis": "variant", "metrics": [sql_metric("Checkout conversion", "MAX(checkout_conversion)")],
                "y_axis_format": ".1%", "show_legend": False, "show_value": True,
            }),
            ("Experiment — Paid conversion", "experiments", "echarts_timeseries_bar", {
                "x_axis": "variant", "metrics": [sql_metric("Paid conversion", "MAX(paid_conversion)")],
                "y_axis_format": ".1%", "show_legend": False, "show_value": True,
            }),
            ("Acquisition — Registrations", "acquisition", "pie", {
                "groupby": ["acquisition_channel"], "metric": sql_metric("Registrations", "SUM(registrations)"),
                "donut": True, "show_legend": True,
            }),
            ("Acquisition — Unit economics", "acquisition", "table", {
                "all_columns": ["acquisition_channel", "registrations", "cac_usd", "observed_contribution_ltv_usd", "ltv_cac"],
                "order_by_cols": [], "row_limit": 100,
            }),
            ("Incident — Payment success rate", "platform_quality", "echarts_timeseries_line", {
                "x_axis": "event_hour", "metrics": [sql_metric("Payment success rate", "AVG(payment_success_rate)")],
                "groupby": ["device_type", "app_version"], "time_grain_sqla": "P1D",
                "y_axis_format": ".0%", "show_legend": True,
            }),
            ("Incident — Attempts by client", "platform_quality", "echarts_timeseries_bar", {
                "x_axis": "event_hour", "metrics": [sql_metric("Payment attempts", "SUM(payment_attempts)")],
                "groupby": ["device_type", "app_version"], "time_grain_sqla": "P1D", "show_legend": True,
            }),
        ]

        common = {
            "adhoc_filters": [], "time_range": "No filter", "row_limit": 10000,
            "order_desc": True, "color_scheme": "supersetColors", "rich_tooltip": True,
            "show_value": False,
        }
        charts: dict[str, Slice] = {}
        for name, dataset_name, viz_type, specific in chart_specs:
            dataset = datasets[dataset_name]
            params = {**common, "datasource": f"{dataset.id}__table", "viz_type": viz_type, **specific}
            chart = db.session.query(Slice).filter_by(slice_name=name).one_or_none()
            if chart is None:
                chart = Slice(slice_name=name)
                db.session.add(chart)
            chart.datasource_id = dataset.id
            chart.datasource_type = "table"
            chart.datasource_name = dataset.table_name
            chart.viz_type = viz_type
            chart.params = json.dumps(params)
            charts[name] = chart
        db.session.commit()

        dashboard_specs = {
            "Executive Dashboard": ["Executive — Net revenue", "Executive — Daily active users", "Executive — LTV / CAC"],
            "Retention Dashboard": ["Retention — Cohort checkpoints"],
            "Experiment Dashboard": ["Experiment — Checkout conversion", "Experiment — Paid conversion"],
            "Acquisition Dashboard": ["Acquisition — Registrations", "Acquisition — Unit economics"],
            "Incident Dashboard": ["Incident — Payment success rate", "Incident — Attempts by client"],
        }
        for title, chart_names in dashboard_specs.items():
            selected = [charts[name] for name in chart_names]
            dashboard = db.session.query(Dashboard).filter_by(dashboard_title=title).one_or_none()
            if dashboard is None:
                dashboard = Dashboard(dashboard_title=title)
                db.session.add(dashboard)
            dashboard.slug = title.lower().replace(" ", "-")
            dashboard.published = True
            dashboard.description = "Synthetic portfolio data; no production or personal information."
            dashboard.json_metadata = json.dumps({"timed_refresh_immune_slices": [], "show_native_filters": True})
            dashboard.slices = selected
            db.session.flush()
            dashboard.position_json = position_json(selected)
        db.session.commit()
        print(f"Provisioned {len(datasets)} datasets, {len(charts)} charts and {len(dashboard_specs)} dashboards")


if __name__ == "__main__":
    main()
