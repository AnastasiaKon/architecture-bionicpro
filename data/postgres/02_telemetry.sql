CREATE SCHEMA IF NOT EXISTS telemetry;

CREATE TABLE telemetry.events (
    id                BIGSERIAL PRIMARY KEY,
    prosthesis_serial TEXT NOT NULL,
    event_ts          TIMESTAMPTZ NOT NULL,
    movement_type     TEXT NOT NULL,
    latency_ms        SMALLINT NOT NULL,
    signal_quality    REAL NOT NULL,
    mio_amplitude_uv  REAL NOT NULL,
    battery_level     SMALLINT NOT NULL
);
CREATE INDEX events_ts_idx ON telemetry.events (event_ts);
CREATE INDEX events_serial_ts_idx ON telemetry.events (prosthesis_serial, event_ts);
INSERT INTO telemetry.events
    (prosthesis_serial, event_ts, movement_type, latency_ms, signal_quality, mio_amplitude_uv, battery_level)
SELECT
    s.serial,
    t.ts,
    (ARRAY['grip', 'release', 'rotate', 'idle'])[1 + floor(random() * 4)::int],
    (60 + random() * 50 + CASE WHEN random() < 0.08 THEN 40 + random() * 60 ELSE 0 END)::smallint,
    round((0.6 + random() * 0.4)::numeric, 3)::real,
    round((80 + random() * 120)::numeric, 1)::real,
    (100 - ((extract(hour from t.ts) * 60 + extract(minute from t.ts)) / 1440.0 * 70))::smallint
FROM (VALUES ('BP-2024-0001'), ('BP-2024-0002'), ('BP-2024-0117'), ('BP-2025-0042')) AS s(serial)
CROSS JOIN generate_series(
    date_trunc('day', now()) - interval '14 days',
    now(),
    interval '10 minutes'
) AS t(ts);
