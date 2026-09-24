"""Incremental, idempotent lightweight warehouse runner.

SQLite is the executable fallback used by tests and by contributors who do not
run the optional Greenplum stack.  The same layer boundaries and grains are
implemented by the Greenplum SQL under ``sql/greenplum``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pyarrow.dataset as ds

from .contracts import load_contract, require_valid
from .security.pii import (
    PII_FIELDS,
    encrypt_value,
    encryption_key_from_env,
    hmac_secret_from_env,
    normalize_email,
    normalize_phone,
    pseudonymize,
)

LOGGER = logging.getLogger(__name__)


class DataQualityGateError(RuntimeError):
    """Raised when a critical warehouse quality rule blocks mart publication."""


@dataclass
class BatchMetadata:
    batch_id: str
    started_at: str
    finished_at: str | None
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    watermark_from: str
    watermark_to: str
    status: str


def _iso(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def _rows(root: Path, table: str, columns: list[str] | None = None) -> Iterator[dict[str, Any]]:
    dataset = ds.dataset(root / "clean" / table, format="parquet")
    for batch in dataset.scanner(columns=columns, batch_size=100_000).to_batches():
        yield from batch.to_pylist()


def _in_interval(value: datetime | date, start: datetime, end: datetime) -> bool:
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return start <= value < end


def _safe_payload(row: dict[str, Any]) -> str:
    """Return useful reject context without copying contact data."""
    safe = {key: ("[REDACTED]" if key in PII_FIELDS else _iso(value)) for key, value in row.items()}
    return json.dumps(safe, sort_keys=True, default=str)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS etl_batch_runs (
  batch_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
  rows_read INTEGER NOT NULL, rows_loaded INTEGER NOT NULL, rows_rejected INTEGER NOT NULL,
  watermark_from TEXT NOT NULL, watermark_to TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine_records (
  source TEXT NOT NULL, record_identifier TEXT, validation_error TEXT NOT NULL,
  rejected_at TEXT NOT NULL, batch_id TEXT NOT NULL, safe_payload TEXT NOT NULL,
  UNIQUE(source, record_identifier, validation_error, batch_id)
);
CREATE TABLE IF NOT EXISTS raw_users (
  user_id TEXT PRIMARY KEY, anonymous_user_id TEXT NOT NULL, email_hmac TEXT NOT NULL,
  phone_hmac TEXT NOT NULL, encrypted_pii TEXT, registration_at TEXT NOT NULL,
  country TEXT NOT NULL, device_type TEXT NOT NULL, acquisition_channel TEXT NOT NULL,
  campaign_id TEXT NOT NULL, initial_plan TEXT NOT NULL,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_events (
  event_id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT NOT NULL, event_time TEXT NOT NULL,
  event_date TEXT NOT NULL, event_name TEXT NOT NULL, feature_name TEXT, device_type TEXT,
  os TEXT, app_version TEXT, experiment_id TEXT, experiment_variant TEXT,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_payments (
  payment_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, subscription_id TEXT NOT NULL,
  payment_at TEXT NOT NULL, amount_usd REAL NOT NULL, refund_amount_usd REAL NOT NULL,
  currency TEXT NOT NULL, status TEXT NOT NULL,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_subscriptions (
  subscription_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL,
  started_at TEXT NOT NULL, ended_at TEXT, monthly_price_usd REAL NOT NULL, status TEXT NOT NULL,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_marketing_spend (
  spend_key TEXT PRIMARY KEY, spend_date TEXT NOT NULL, channel TEXT NOT NULL, campaign_id TEXT NOT NULL,
  country TEXT NOT NULL, spend_usd REAL NOT NULL, attributed_signups INTEGER NOT NULL,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_experiment_assignments (
  experiment_id TEXT NOT NULL, user_id TEXT NOT NULL, variant TEXT NOT NULL, assigned_at TEXT NOT NULL,
  ingestion_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL, source TEXT NOT NULL, source_file TEXT NOT NULL,
  PRIMARY KEY(experiment_id, user_id)
);

CREATE VIEW IF NOT EXISTS stg_users AS
SELECT user_id, anonymous_user_id, registration_at, country, device_type,
       acquisition_channel, campaign_id, initial_plan FROM raw_users;
CREATE VIEW IF NOT EXISTS stg_events AS
SELECT * FROM raw_events WHERE user_id IS NOT NULL AND event_name <> '';
CREATE VIEW IF NOT EXISTS stg_payments AS
SELECT * FROM raw_payments WHERE amount_usd >= 0 AND refund_amount_usd >= 0;

CREATE TABLE IF NOT EXISTS dim_users (
  user_id TEXT PRIMARY KEY, anonymous_user_id TEXT NOT NULL UNIQUE, registration_at TEXT NOT NULL,
  country TEXT NOT NULL, device_type TEXT NOT NULL, acquisition_channel TEXT NOT NULL, campaign_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_plans (plan TEXT PRIMARY KEY, plan_rank INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS dim_campaigns (campaign_id TEXT PRIMARY KEY, channel TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dim_date (date_key TEXT PRIMARY KEY, year INTEGER, month INTEGER, day INTEGER);
CREATE TABLE IF NOT EXISTS dim_user_plan_history (
  user_sk TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL,
  valid_from TEXT NOT NULL, valid_to TEXT, is_current INTEGER NOT NULL,
  UNIQUE(user_id, valid_from), FOREIGN KEY(user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS fct_events (
  event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, event_time TEXT NOT NULL, event_date TEXT NOT NULL,
  event_name TEXT NOT NULL, feature_name TEXT, device_type TEXT, app_version TEXT,
  experiment_id TEXT, experiment_variant TEXT,
  FOREIGN KEY(user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS fct_payments (
  payment_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, subscription_id TEXT NOT NULL,
  payment_at TEXT NOT NULL, amount_usd REAL NOT NULL, refund_amount_usd REAL NOT NULL,
  currency TEXT NOT NULL, status TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS fct_subscriptions (
  subscription_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL,
  started_at TEXT NOT NULL, ended_at TEXT, monthly_price_usd REAL NOT NULL, status TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES dim_users(user_id)
);
CREATE TABLE IF NOT EXISTS fct_experiments (
  experiment_id TEXT NOT NULL, user_id TEXT NOT NULL, variant TEXT NOT NULL, assigned_at TEXT NOT NULL,
  PRIMARY KEY(experiment_id, user_id)
);

CREATE TABLE IF NOT EXISTS mart_revenue_daily (
  payment_date TEXT PRIMARY KEY, gross_revenue_usd REAL NOT NULL, refunds_usd REAL NOT NULL,
  net_revenue_usd REAL NOT NULL, paid_users INTEGER NOT NULL, arppu_usd REAL
);
CREATE TABLE IF NOT EXISTS mart_product_daily (
  event_date TEXT PRIMARY KEY, active_users INTEGER NOT NULL, signups INTEGER NOT NULL,
  activated_users INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS mart_pipeline_health (
  batch_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, duration_seconds REAL,
  status TEXT NOT NULL, rows_processed INTEGER NOT NULL, freshness_seconds REAL, sla_met INTEGER NOT NULL
);
"""


class WarehousePipeline:
    """Build raw, staging, core and mart layers from generated Parquet."""

    def __init__(self, database: Path, hmac_secret: str | None = None, encryption_key: str | None = None):
        self.database = database
        self.hmac_secret = hmac_secret or hmac_secret_from_env()
        self.encryption_key = encryption_key if encryption_key is not None else encryption_key_from_env()

    def run(
        self,
        source: Path,
        watermark_from: datetime,
        watermark_to: datetime,
        batch_id: str | None = None,
    ) -> BatchMetadata:
        source = source.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        batch_id = batch_id or hashlib.sha256(
            f"{source}|{watermark_from.isoformat()}|{watermark_to.isoformat()}".encode()
        ).hexdigest()[:24]
        started = datetime.now(timezone.utc)
        metadata = BatchMetadata(batch_id, started.isoformat(), None, 0, 0, 0,
                                 watermark_from.isoformat(), watermark_to.isoformat(), "running")
        with sqlite3.connect(self.database) as connection:
            connection.executescript(SCHEMA_SQL)
            self._save_metadata(connection, metadata)
            try:
                self._ingest(connection, source, watermark_from, watermark_to, metadata)
                self._build_core(connection)
                self._apply_scd2(connection)
                self._quality_gate(connection)
                metadata.status = "success"
                metadata.finished_at = datetime.now(timezone.utc).isoformat()
                self._save_metadata(connection, metadata)
                self._build_marts(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                metadata.status = "failed"
                raise
            finally:
                if metadata.finished_at is None:
                    metadata.finished_at = datetime.now(timezone.utc).isoformat()
                self._save_metadata(connection, metadata)
                connection.commit()
        LOGGER.info("warehouse batch %s: %s", batch_id, asdict(metadata))
        return metadata

    @staticmethod
    def _save_metadata(connection: sqlite3.Connection, item: BatchMetadata) -> None:
        connection.execute(
            """INSERT INTO etl_batch_runs VALUES (:batch_id,:started_at,:finished_at,:rows_read,
               :rows_loaded,:rows_rejected,:watermark_from,:watermark_to,:status)
               ON CONFLICT(batch_id) DO UPDATE SET started_at=excluded.started_at,
               finished_at=excluded.finished_at, rows_read=excluded.rows_read,
               rows_loaded=excluded.rows_loaded, rows_rejected=excluded.rows_rejected,
               watermark_from=excluded.watermark_from, watermark_to=excluded.watermark_to,
               status=excluded.status""",
            asdict(item),
        )

    def _ingest(
        self,
        connection: sqlite3.Connection,
        source: Path,
        start: datetime,
        end: datetime,
        metadata: BatchMetadata,
    ) -> None:
        loaded_at = datetime.now(timezone.utc).isoformat()
        for table, timestamp in (
            ("users", "registration_at"), ("events", "event_time"),
            ("payments", "payment_at"), ("subscriptions", "started_at"),
            ("marketing_spend", "date"), ("experiment_assignments", "assigned_at"),
        ):
            contract = load_contract(table)
            for row in _rows(source, table):
                if not _in_interval(row[timestamp], start, end):
                    continue
                metadata.rows_read += 1
                try:
                    require_valid(row, contract)
                    self._load_row(connection, table, row, loaded_at, metadata.batch_id)
                    metadata.rows_loaded += 1
                except (KeyError, TypeError, ValueError) as exc:
                    identifier = next((row.get(k) for k in ("event_id", "payment_id", "subscription_id", "user_id")), None)
                    connection.execute(
                        "INSERT OR IGNORE INTO quarantine_records VALUES (?,?,?,?,?,?)",
                        (table, identifier, str(exc), loaded_at, metadata.batch_id, _safe_payload(row)),
                    )
                    metadata.rows_rejected += 1

    def _load_row(
        self, connection: sqlite3.Connection, table: str, row: dict[str, Any], loaded_at: str, batch_id: str
    ) -> None:
        tech = (loaded_at, batch_id, "synthetic_parquet", f"clean/{table}")
        if table == "users":
            email = normalize_email(row["email"])
            phone = normalize_phone(row["phone"])
            anonymous = pseudonymize(row["user_id"], self.hmac_secret)
            encrypted = None
            if self.encryption_key:
                encrypted = encrypt_value(json.dumps({k: row[k] for k in PII_FIELDS}, sort_keys=True), self.encryption_key)
            values = (
                row["user_id"], anonymous, pseudonymize(email, self.hmac_secret),
                pseudonymize(phone, self.hmac_secret), encrypted, _iso(row["registration_at"]),
                row["country"], row["device_type"], row["acquisition_channel"], row["campaign_id"],
                row["initial_plan"], *tech,
            )
            connection.execute("INSERT OR REPLACE INTO raw_users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        elif table == "events":
            if not row.get("user_id"):
                raise ValueError("event user_id is required by the analytical warehouse")
            values = tuple(_iso(row.get(k)) for k in (
                "event_id", "user_id", "session_id", "event_time", "event_date", "event_name", "feature_name",
                "device_type", "os", "app_version", "experiment_id", "experiment_variant",
            )) + tech
            connection.execute("INSERT OR REPLACE INTO raw_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        elif table == "payments":
            if float(row["amount_usd"]) < 0 or float(row["refund_amount_usd"]) < 0:
                raise ValueError("payment amounts cannot be negative")
            values = tuple(_iso(row[k]) for k in (
                "payment_id", "user_id", "subscription_id", "payment_at", "amount_usd",
                "refund_amount_usd", "currency", "status",
            )) + tech
            connection.execute("INSERT OR REPLACE INTO raw_payments VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", values)
        elif table == "subscriptions":
            if row.get("ended_at") and row["ended_at"] < row["started_at"]:
                raise ValueError("subscription ended_at precedes started_at")
            values = tuple(_iso(row.get(k)) for k in (
                "subscription_id", "user_id", "plan", "started_at", "ended_at", "monthly_price_usd", "status",
            )) + tech
            connection.execute("INSERT OR REPLACE INTO raw_subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
        elif table == "marketing_spend":
            key = "|".join(str(_iso(row[k])) for k in ("date", "channel", "campaign_id", "country"))
            values = (key, _iso(row["date"]), row["channel"], row["campaign_id"], row["country"],
                      float(row["spend_usd"]), int(row["attributed_signups"]), *tech)
            connection.execute("INSERT OR REPLACE INTO raw_marketing_spend VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
        else:
            values = tuple(_iso(row[k]) for k in ("experiment_id", "user_id", "variant", "assigned_at")) + tech
            connection.execute(
                "INSERT OR REPLACE INTO raw_experiment_assignments VALUES (?,?,?,?,?,?,?,?)", values
            )

    @staticmethod
    def _build_core(connection: sqlite3.Connection) -> None:
        connection.execute("INSERT OR IGNORE INTO dim_plans VALUES ('free',0),('basic',1),('pro',2)")
        connection.execute(
            """INSERT OR REPLACE INTO dim_users
               SELECT user_id,anonymous_user_id,registration_at,country,device_type,acquisition_channel,campaign_id
               FROM stg_users"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO dim_campaigns
               SELECT campaign_id, MIN(acquisition_channel) FROM stg_users GROUP BY campaign_id"""
        )
        connection.execute(
            """INSERT OR IGNORE INTO dim_date
               SELECT DISTINCT event_date,CAST(substr(event_date,1,4) AS INTEGER),
               CAST(substr(event_date,6,2) AS INTEGER),CAST(substr(event_date,9,2) AS INTEGER) FROM stg_events"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO fct_events
               SELECT event_id,user_id,event_time,event_date,event_name,feature_name,device_type,app_version,
               experiment_id,experiment_variant FROM stg_events"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO fct_payments
               SELECT payment_id,user_id,subscription_id,payment_at,amount_usd,refund_amount_usd,currency,status
               FROM stg_payments"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO fct_subscriptions
               SELECT subscription_id,user_id,plan,started_at,ended_at,monthly_price_usd,status
               FROM raw_subscriptions"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO fct_experiments
               SELECT experiment_id,user_id,variant,assigned_at FROM raw_experiment_assignments"""
        )

    @staticmethod
    def _apply_scd2(connection: sqlite3.Connection) -> None:
        users = connection.execute("SELECT user_id,registration_at,initial_plan FROM raw_users").fetchall()
        for user_id, registered, initial_plan in users:
            changes = [(registered, initial_plan)] + connection.execute(
                "SELECT started_at,plan FROM raw_subscriptions WHERE user_id=? ORDER BY started_at", (user_id,)
            ).fetchall()
            collapsed: list[tuple[str, str]] = []
            for valid_from, plan in changes:
                if not collapsed or collapsed[-1][1] != plan:
                    collapsed.append((valid_from, plan))
            connection.execute("DELETE FROM dim_user_plan_history WHERE user_id=?", (user_id,))
            for index, (valid_from, plan) in enumerate(collapsed):
                valid_to = collapsed[index + 1][0] if index + 1 < len(collapsed) else None
                user_sk = hashlib.sha256(f"{user_id}|{valid_from}".encode()).hexdigest()[:24]
                connection.execute(
                    "INSERT INTO dim_user_plan_history VALUES (?,?,?,?,?,?)",
                    (user_sk, user_id, plan, valid_from, valid_to, int(valid_to is None)),
                )

    @staticmethod
    def _quality_gate(connection: sqlite3.Connection) -> None:
        checks = {
            "duplicate_event_id": "SELECT COUNT(*)-COUNT(DISTINCT event_id) FROM fct_events",
            "orphan_event_user": "SELECT COUNT(*) FROM fct_events e LEFT JOIN dim_users u USING(user_id) WHERE u.user_id IS NULL",
            "orphan_payment_user": "SELECT COUNT(*) FROM fct_payments p LEFT JOIN dim_users u USING(user_id) WHERE u.user_id IS NULL",
            "negative_payment": "SELECT COUNT(*) FROM fct_payments WHERE amount_usd<0 OR refund_amount_usd<0",
            "multiple_current_scd2": "SELECT COUNT(*) FROM (SELECT user_id FROM dim_user_plan_history WHERE is_current=1 GROUP BY user_id HAVING COUNT(*)<>1)",
        }
        failures = {name: connection.execute(sql).fetchone()[0] for name, sql in checks.items()}
        failed = {name: count for name, count in failures.items() if count}
        if failed:
            raise DataQualityGateError(f"critical DQ gate failed: {failed}")

    @staticmethod
    def _build_marts(connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM mart_revenue_daily")
        connection.execute(
            """INSERT INTO mart_revenue_daily
               SELECT substr(payment_at,1,10),
                      SUM(CASE WHEN status IN ('success','refunded') THEN amount_usd ELSE 0 END),
                      SUM(refund_amount_usd),
                      SUM(CASE WHEN status IN ('success','refunded') THEN amount_usd-refund_amount_usd ELSE 0 END),
                      COUNT(DISTINCT CASE WHEN status IN ('success','refunded') THEN user_id END),
                      SUM(CASE WHEN status IN ('success','refunded') THEN amount_usd-refund_amount_usd ELSE 0 END)
                        / NULLIF(COUNT(DISTINCT CASE WHEN status IN ('success','refunded') THEN user_id END),0)
               FROM fct_payments GROUP BY substr(payment_at,1,10)"""
        )
        connection.execute("DELETE FROM mart_product_daily")
        connection.execute(
            """INSERT INTO mart_product_daily
               SELECT event_date,COUNT(DISTINCT user_id),
                      COUNT(DISTINCT CASE WHEN event_name='signup' THEN user_id END),
                      COUNT(DISTINCT CASE WHEN event_name='onboarding_completed' THEN user_id END)
               FROM fct_events GROUP BY event_date"""
        )
        connection.execute("DELETE FROM mart_pipeline_health")
        connection.execute(
            """INSERT INTO mart_pipeline_health
               SELECT batch_id,started_at,finished_at,
                      (julianday(finished_at)-julianday(started_at))*86400,status,rows_loaded,
                      (julianday(finished_at)-julianday(watermark_to))*86400,
                      CASE WHEN status='success' AND
                         (julianday(finished_at)-julianday(started_at))*1440<=45 THEN 1 ELSE 0 END
               FROM etl_batch_runs WHERE finished_at IS NOT NULL"""
        )


def run_from_manifest(source: Path, database: Path, batch_id: str | None = None) -> BatchMetadata:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    start = datetime.fromisoformat(str(manifest["period_start"]))
    end = datetime.fromisoformat(str(manifest["period_end"]))
    return WarehousePipeline(database).run(source, start, end, batch_id=batch_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local raw/staging/core/marts warehouse")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=Path("data/warehouse.db"))
    parser.add_argument("--batch-id")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run_from_manifest(args.input, args.database, args.batch_id)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
