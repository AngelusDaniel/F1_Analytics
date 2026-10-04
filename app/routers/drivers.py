from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Driver, Race, Result
from app.schemas import DriverOut, DriverResultOut

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverOut])
def list_drivers(
    q: Optional[str] = Query(None, description="Busca por nome ou sobrenome"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Driver).order_by(Driver.family_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Driver.family_name.ilike(like), Driver.given_name.ilike(like))
        )
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(driver_id: str, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Piloto não encontrado")
    return driver


@router.get("/{driver_id}/results", response_model=list[DriverResultOut])
def driver_results(
    driver_id: str,
    season: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if db.get(Driver, driver_id) is None:
        raise HTTPException(status_code=404, detail="Piloto não encontrado")

    stmt = (
        select(Race.season, Race.round, Race.name, Result)
        .join(Result, Result.race_id == Race.id)
        .where(Result.driver_id == driver_id)
        .order_by(Race.date)
    )
    if season is not None:
        stmt = stmt.where(Race.season == season)

    return [
        DriverResultOut(
            season=s,
            round=rnd,
            race_name=name,
            grid=res.grid,
            position=res.position,
            points=res.points,
            constructor_name=res.constructor_name,
            status=res.status,
        )
        for s, rnd, name, res in db.execute(stmt).all()
    ]
