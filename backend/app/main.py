from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import olap
from .auth import Principal, require_prosthesis_user
from .config import settings

app = FastAPI(title="BionicPRO reports-api", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)


class ReportRowOut(BaseModel):
    report_date: date
    prosthesis_serial: str
    model: str
    events_count: int
    avg_latency_ms: float
    max_latency_ms: int
    slow_responses_count: int
    avg_signal_quality: float
    min_battery_level: int


class ReportOut(BaseModel):
    username: str
    full_name: str
    date_from: date
    date_to: date
    processed_until: datetime
    truncated: bool
    generated_at: datetime
    rows: list[ReportRowOut]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/reports", response_model=ReportOut)
def get_report(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    user: str | None = Query(None),
    principal: Principal = Depends(require_prosthesis_user),
) -> ReportOut:
    if user is not None and user != principal.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may request only your own report",
        )
    username = principal.username

    processed_until = olap.get_processed_until()
    if processed_until is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report mart is not built yet - wait for the ETL run",
        )
    processed_date = (processed_until - timedelta(seconds=1)).date()

    if date_to is None:
        date_to = processed_date
    if date_from is None:
        date_from = date_to - timedelta(days=6)

    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must not be after date_to",
        )
    if (date_to - date_from).days > settings.max_period_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Period is limited to {settings.max_period_days} days",
        )
    if date_from > processed_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Requested period is not processed yet. "
                f"Data is available until {processed_date.isoformat()}"
            ),
        )
    truncated = date_to > processed_date
    if truncated:
        date_to = processed_date

    rows = olap.get_user_report(username, date_from, date_to)
    full_name = olap.get_user_full_name(username) or username

    return ReportOut(
        username=username,
        full_name=full_name,
        date_from=date_from,
        date_to=date_to,
        processed_until=processed_until,
        truncated=truncated,
        generated_at=datetime.now(timezone.utc),
        rows=[ReportRowOut(**row.__dict__) for row in rows],
    )
