from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_db
from app.models import Race, Result
from app.schemas import RaceDetail, RaceOut

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=list[RaceOut])
def list_races(
    season: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Race).options(joinedload(Race.circuit)).order_by(Race.date.desc())
    if season is not None:
        stmt = stmt.where(Race.season == season)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{season}/{round}", response_model=RaceDetail)
def get_race(season: int, round: int, db: Session = Depends(get_db)):
    stmt = (
        select(Race)
        .where(Race.season == season, Race.round == round)
        .options(
            joinedload(Race.circuit),
            selectinload(Race.results).joinedload(Result.driver),
        )
    )
    race = db.scalar(stmt)
    if race is None:
        raise HTTPException(status_code=404, detail="Corrida não encontrada")

    detail = RaceDetail.model_validate(race)
    # quem não foi classificado (position None) vai para o fim da lista
    detail.results.sort(key=lambda r: (r.position is None, r.position or 0))
    return detail
