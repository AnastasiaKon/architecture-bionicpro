CREATE TABLE IF NOT EXISTS raw_telemetry_events
(
    event_id          UInt64,
    prosthesis_serial LowCardinality(String),
    event_ts          DateTime,
    movement_type     LowCardinality(String),
    latency_ms        UInt16,
    signal_quality    Float32,
    mio_amplitude_uv  Float32,
    battery_level     UInt8,
    loaded_at         DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
PARTITION BY toYYYYMM(event_ts)
ORDER BY (prosthesis_serial, event_ts, event_id);
CREATE TABLE IF NOT EXISTS crm_customers
(
    customer_id UInt32,
    username    String,
    full_name   String,
    email       String,
    country     FixedString(2),
    loaded_at   DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY username;
CREATE TABLE IF NOT EXISTS crm_prostheses
(
    prosthesis_id     UInt32,
    customer_id       UInt32,
    username          String,
    prosthesis_serial String,
    model             String,
    side              LowCardinality(String),
    delivered_at      Date,
    loaded_at         DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY prosthesis_serial;
CREATE TABLE IF NOT EXISTS prosthesis_usage_report
(
    username              String,
    report_date           Date,
    prosthesis_serial     String,
    model                 String,
    events_count          UInt32,
    avg_latency_ms        Float32,
    max_latency_ms        UInt16,
    slow_responses_count  UInt32,
    avg_signal_quality    Float32,
    avg_mio_amplitude_uv  Float32,
    min_battery_level     UInt8,
    etl_run_ts            DateTime
)
ENGINE = ReplacingMergeTree(etl_run_ts)
PARTITION BY toYYYYMM(report_date)
ORDER BY (username, report_date, prosthesis_serial);
CREATE TABLE IF NOT EXISTS etl_watermark
(
    processed_until DateTime,
    dag_run_id      String,
    updated_at      DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY updated_at;
