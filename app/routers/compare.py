from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Driver, LapTelemetry, Race, Result
from app.schemas import Channels, CompareOut, LapSummary, Track

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/available", response_model=list[str])
def available_drivers(
    season: int,
    round_number: int = Query(..., alias="round"),
    session: Literal["Q", "R"] = "Q",
    db: Session = Depends(get_db),
):
    """Códigos de pilotos com telemetria disponível (para montar dropdowns)."""
    stmt = (
        select(Driver.code)
        .join(LapTelemetry, LapTelemetry.driver_id == Driver.id)
        .join(Race, LapTelemetry.race_id == Race.id)
        .where(
            Race.season == season,
            Race.round == round_number,
            LapTelemetry.session == session,
        )
        .order_by(Driver.code)
    )
    return db.scalars(stmt).all()


@router.get("", response_model=CompareOut)
def compare(
    season: int,
    round_number: int = Query(..., alias="round"),
    d1: str = Query(..., min_length=3, max_length=3, description="Ex: VER"),
    d2: str = Query(..., min_length=3, max_length=3, description="Ex: NOR"),
    session: Literal["Q", "R"] = "Q",
    db: Session = Depends(get_db),
):
    d1, d2 = d1.upper(), d2.upper()
    if d1 == d2:
        raise HTTPException(status_code=400, detail="Escolha dois pilotos diferentes")

    stmt = (
        select(LapTelemetry)
        .join(Driver, LapTelemetry.driver_id == Driver.id)
        .join(Race, LapTelemetry.race_id == Race.id)
        .where(
            Race.season == season,
            Race.round == round_number,
            LapTelemetry.session == session,
            Driver.code.in_([d1, d2]),
        )
        .options(joinedload(LapTelemetry.driver), joinedload(LapTelemetry.race))
    )
    laps = {lap.driver.code: lap for lap in db.scalars(stmt).all()}

    missing = [c for c in (d1, d2) if c not in laps]
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Sem telemetria para: {', '.join(missing)}"
        )

    a, b = laps[d1], laps[d2]
    delta = [round(tb - ta, 3) for ta, tb in zip(a.data["time"], b.data["time"])]

    # equipe de cada piloto nessa corrida (define a cor no dashboard)
    teams = dict(
        db.execute(
            select(Result.driver_id, Result.constructor_id).where(
                Result.race_id == a.race_id,
                Result.driver_id.in_([a.driver_id, b.driver_id]),
            )
        ).all()
    )

    return CompareOut(
        season=season,
        round=round_number,
        race_name=a.race.name,
        session=session,
        drivers=[
            LapSummary(
                code=lap.driver.code,
                name=f"{lap.driver.given_name} {lap.driver.family_name}",
                lap_time=lap.lap_time,
                compound=lap.compound,
                team=teams.get(lap.driver_id),
            )
            for lap in (a, b)
        ],
        distance=a.data["distance"],
        telemetry={
            lap.driver.code: Channels(**{k: lap.data[k] for k in Channels.model_fields})
            for lap in (a, b)
        },
        delta=delta,
        track=Track(x=a.data["x"], y=a.data["y"]),
    )
