import os


class Settings:
    keycloak_issuer: str = os.getenv(
        "KEYCLOAK_ISSUER", "http://localhost:8080/realms/reports-realm"
    )
    keycloak_jwks_url: str = os.getenv(
        "KEYCLOAK_JWKS_URL",
        "http://keycloak:8080/realms/reports-realm/protocol/openid-connect/certs",
    )
    keycloak_audience: str = os.getenv("KEYCLOAK_AUDIENCE", "reports-api")
    required_role: str = os.getenv("REPORTS_REQUIRED_ROLE", "prothetic_user")

    clickhouse_host: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    clickhouse_user: str = os.getenv("CLICKHOUSE_USER", "reports")
    clickhouse_password: str = os.getenv("CLICKHOUSE_PASSWORD", "reports")
    clickhouse_db: str = os.getenv("CLICKHOUSE_DB", "reports")

    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]

    max_period_days: int = int(os.getenv("REPORTS_MAX_PERIOD_DAYS", "92"))


settings = Settings()
