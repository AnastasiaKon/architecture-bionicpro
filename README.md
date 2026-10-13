# BionicPRO - проектная работа 9 спринта

- Задание 1: `docs/diagrams/task1-identity-c4.drawio`, PKCE - `keycloak/realm-export.json`, `frontend/src/App.tsx`
- Задание 2: `docs/diagrams/task2-reports-c4.drawio`, ETL - `airflow/`, API - `backend/`, UI - `frontend/src/components/ReportPage.tsx`

## Запуск

```bash
docker compose up --build -d
```

| Сервис | URL | Доступ |
|---|---|---|
| Frontend | http://localhost:3000 | `prothetic1` / `prothetic123` |
| Keycloak | http://localhost:8080 | `admin` / `admin` |
| reports-api | http://localhost:8000/docs | Bearer-токен Keycloak |
| Airflow | http://localhost:8081 | `admin` / `admin` |
| ClickHouse | http://localhost:8123 | `reports` / `reports` |

1. В Airflow включить и запустить DAG `bionicpro_reports_etl`.
2. На http://localhost:3000 войти, выбрать период, нажать Generate Report.
