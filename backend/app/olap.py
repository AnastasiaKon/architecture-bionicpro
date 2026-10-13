from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .config import settings


@lru_cache(maxsize=1)
def get_client() -> Client:
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )


@dataclass
class ReportRow:
    report_date: date
    prosthesis_serial: str
    model: str
    events_count: int
    avg_latency_ms: float
    max_latency_ms: int
    slow_responses_count: int
    avg_signal_quality: float
    min_battery_level: int


def get_processed_until() -> datetime | None:
    result = get_client().query("SELECT max(processed_until) FROM etl_watermark")
    value = result.result_rows[0][0] if result.result_rows else None
    if value is None or value.year <= 1970:
        return None
    return value


def get_user_full_name(username: str) -> str | None:
    result = get_client().query(
        "SELECT full_name FROM crm_customers WHERE username = {u:String} LIMIT 1",
        parameters={"u": username},
    )
    return result.result_rows[0][0] if result.result_rows else None


def get_user_report(username: str, date_from: date, date_to: date) -> list[ReportRow]:
    query = """
        SELECT
            report_date,
            prosthesis_serial,
            model,
            events_count,
            round(avg_latency_ms, 2)      AS avg_latency_ms,
            max_latency_ms,
            slow_responses_count,
            round(avg_signal_quality, 3)  AS avg_signal_quality,
            min_battery_level
        FROM prosthesis_usage_report FINAL
        WHERE username = {u:String}
          AND report_date BETWEEN {d_from:Date} AND {d_to:Date}
        ORDER BY report_date, prosthesis_serial
    """
    result = get_client().query(
        query, parameters={"u": username, "d_from": date_from, "d_to": date_to}
    )
    return [ReportRow(*row) for row in result.result_rows]
