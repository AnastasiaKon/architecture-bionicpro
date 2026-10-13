CREATE SCHEMA IF NOT EXISTS crm;

CREATE TABLE crm.customers (
    id          SERIAL PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL,
    country     CHAR(2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE crm.prostheses (
    id             SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES crm.customers(id),
    serial_number  TEXT NOT NULL UNIQUE,
    model          TEXT NOT NULL,
    side           TEXT NOT NULL CHECK (side IN ('left', 'right')),
    delivered_at   DATE NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO crm.customers (username, full_name, email, country) VALUES
    ('prothetic1', 'Prothetic One',   'prothetic1@example.com', 'RU'),
    ('prothetic2', 'Prothetic Two',   'prothetic2@example.com', 'RU'),
    ('prothetic3', 'Prothetic Three', 'prothetic3@example.com', 'KZ');

INSERT INTO crm.prostheses (customer_id, serial_number, model, side, delivered_at) VALUES
    (1, 'BP-2024-0001', 'BionicHand Pro 2',  'right', '2024-03-12'),
    (1, 'BP-2024-0002', 'BionicHand Pro 2',  'left',  '2024-03-12'),
    (2, 'BP-2024-0117', 'BionicHand Lite',   'right', '2024-09-01'),
    (3, 'BP-2025-0042', 'BionicHand Pro 3',  'left',  '2025-02-20');
