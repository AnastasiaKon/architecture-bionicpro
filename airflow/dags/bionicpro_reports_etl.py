from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import clickhouse_connect
import pendulum
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

log = logging.getLogger(__name__)

CRM_CONN_ID = "crm_postgres"
TELEMETRY_CONN_ID = "telemetry_postgres"
DDL_PATH = Path(__file__).parent / "sql" / "mart_ddl.sql"
EPOCH = datetime(1970, 1, 1)
BATCH_ROWS = 50_000


def ch_client():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "reports"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "reports"),
        database=os.getenv("CLICKHOUSE_DB", "reports"),
    )


@dag(
    dag_id="bionicpro_reports_etl",
    description="CRM + телеметрия протезов -> витрина отчётов в ClickHouse",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["bionicpro", "reports", "clickhouse"],
)
def bionicpro_reports_etl():
    @task
    def ensure_schema() -> None:
        ch = ch_client()
        for statement in DDL_PATH.read_text(encoding="utf-8").split(";"):
            if statement.strip():
                ch.command(statement)

    @task
    def load_crm() -> int:
        pg = PostgresHook(postgres_conn_id=CRM_CONN_ID)
        ch = ch_client()

        customers = pg.get_records(
            "SELECT id, username, full_name, email, country FROM crm.customers"
        )
        ch.insert(
            "crm_customers",
            [list(r) for r in customers],
            column_names=["customer_id", "username", "full_name", "email", "country"],
        )

        prostheses = pg.get_records(
            """
            SELECT p.id, p.customer_id, c.username, p.serial_number, p.model, p.side, p.delivered_at
            FROM crm.prostheses p
            JOIN crm.customers c ON c.id = p.customer_id
            """
        )
        ch.insert(
            "crm_prostheses",
            [list(r) for r in prostheses],
            column_names=[
                "prosthesis_id", "customer_id", "username", "prosthesis_serial",
                "model", "side", "delivered_at",
            ],
        )
        ch.command("OPTIMIZE TABLE crm_customers FINAL")
        ch.command("OPTIMIZE TABLE crm_prostheses FINAL")
        log.info("CRM snapshot loaded: %d customers, %d prostheses", len(customers), len(prostheses))
        return len(prostheses)

    @task
    def load_telemetry(data_interval_end: datetime | None = None) -> dict:
        ch = ch_client()
        until = data_interval_end.replace(tzinfo=None) if data_interval_end else datetime.utcnow()

        wm = ch.query("SELECT max(processed_until) FROM etl_watermark").result_rows[0][0]
        since = wm if wm and wm.year > 1970 else EPOCH
        log.info("Extracting telemetry window [%s, %s)", since, until)

        pg = PostgresHook(postgres_conn_id=TELEMETRY_CONN_ID)
        total = 0
        conn = pg.get_conn()
        try:
            with conn.cursor(name="telemetry_stream") as cur:
                cur.itersize = BATCH_ROWS
                cur.execute(
                    """
                    SELECT id, prosthesis_serial,
                           (event_ts AT TIME ZONE 'UTC') AS event_ts,
                           movement_type, latency_ms, signal_quality,
                           mio_amplitude_uv, battery_level
                    FROM telemetry.events
                    WHERE event_ts >= %s AND event_ts < %s
                    ORDER BY id
                    """,
                    (since, until),
                )
                while True:
                    batch = cur.fetchmany(BATCH_ROWS)
                    if not batch:
                        break
                    ch.insert(
                        "raw_telemetry_events",
                        [list(r) for r in batch],
                        column_names=[
                            "event_id", "prosthesis_serial", "event_ts", "movement_type",
                            "latency_ms", "signal_quality", "mio_amplitude_uv", "battery_level",
                        ],
                    )
                    total += len(batch)
        finally:
            conn.close()

        log.info("Loaded %d telemetry events", total)
        return {"since": since.isoformat(), "until": until.isoformat(), "rows": total}

    @task
    def build_report_mart(window: dict) -> int:
        ch = ch_client()
        since = datetime.fromisoformat(window["since"])
        until = datetime.fromisoformat(window["until"])
        day_from = since.date() if since > EPOCH else None
        day_to = (until - timedelta(seconds=1)).date()
        run_ts = datetime.utcnow().replace(microsecond=0)

        date_filter = "toDate(e.event_ts) <= {day_to:Date}"
        params = {"day_to": day_to, "run_ts": run_ts}
        if day_from:
            date_filter += " AND toDate(e.event_ts) >= {day_from:Date}"
            params["day_from"] = day_from

        ch.command(
            f"""
            INSERT INTO prosthesis_usage_report
            SELECT
                p.username,
                toDate(e.event_ts)                      AS report_date,
                e.prosthesis_serial,
                any(p.model)                            AS model,
                count()                                 AS events_count,
                avg(e.latency_ms)                       AS avg_latency_ms,
                max(e.latency_ms)                       AS max_latency_ms,
                countIf(e.latency_ms > 100)             AS slow_responses_count,
                avg(e.signal_quality)                   AS avg_signal_quality,
                avg(e.mio_amplitude_uv)                 AS avg_mio_amplitude_uv,
                min(e.battery_level)                    AS min_battery_level,
                {{run_ts:DateTime}}                     AS etl_run_ts
            FROM raw_telemetry_events AS e FINAL
            INNER JOIN crm_prostheses AS p FINAL
                ON p.prosthesis_serial = e.prosthesis_serial
            WHERE {date_filter}
            GROUP BY p.username, report_date, e.prosthesis_serial
            """,
            parameters=params,
        )
        ch.command("OPTIMIZE TABLE prosthesis_usage_report FINAL")
        rows = ch.query(
            "SELECT count() FROM prosthesis_usage_report FINAL WHERE etl_run_ts = {run_ts:DateTime}",
            parameters={"run_ts": run_ts},
        ).result_rows[0][0]
        log.info("Mart rebuilt for %s..%s: %d rows", day_from or "beginning", day_to, rows)
        return rows

    @task
    def update_watermark(window: dict, run_id: str | None = None) -> None:
        ch_client().insert(
            "etl_watermark",
            [[datetime.fromisoformat(window["until"]), run_id or ""]],
            column_names=["processed_until", "dag_run_id"],
        )

    schema = ensure_schema()
    crm = load_crm()
    window = load_telemetry()
    mart = build_report_mart(window)

    schema >> [crm, window]
    crm >> mart
    mart >> update_watermark(window)


bionicpro_reports_etl()
