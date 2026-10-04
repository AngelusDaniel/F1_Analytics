"""Ingere a volta mais rápida de cada piloto (FastF1) no banco.

Uso:
    python -m scripts.ingest_telemetry --season 2023 --round 1
    python -m scripts.ingest_telemetry --season 2023            # todas as rodadas
    python -m scripts.ingest_telemetry --season 2023 --session R

Rode antes: python -m scripts.ingest (precisa das corridas e pilotos no banco).
"""
import argparse
import os

import fastf1
import pandas as pd
from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Base, Driver, LapTelemetry, Race
from scripts.resample import resample

CACHE_DIR = "cache"


def ingest_round(db, season: int, rnd: int, session_type: str) -> int:
    race = db.scalar(select(Race).where(Race.season == season, Race.round == rnd))
    if race is None:
        print(f"  rodada {rnd}: não está no banco, rode scripts.ingest antes")
        return 0

    session = fastf1.get_session(season, rnd, session_type)
    session.load(laps=True, telemetry=True, weather=False, messages=False)

    saved = 0
    for code in session.laps["Driver"].unique():
        driver = db.scalar(select(Driver).where(Driver.code == code))
        if driver is None:
            print(f"  piloto {code} não encontrado no banco, pulando")
            continue

        lap = session.laps.pick_drivers(code).pick_fastest()
        if lap is None or pd.isna(lap["LapTime"]):
            continue

        try:
            tel = lap.get_telemetry()
        except Exception as exc:  # telemetria ausente em algumas voltas
            print(f"  {code}: sem telemetria ({exc})")
            continue

        row = db.scalar(
            select(LapTelemetry).where(
                LapTelemetry.race_id == race.id,
                LapTelemetry.driver_id == driver.id,
                LapTelemetry.session == session_type,
            )
        )
        if row is None:
            row = LapTelemetry(
                race_id=race.id, driver_id=driver.id, session=session_type
            )
            db.add(row)
        row.lap_time = lap["LapTime"].total_seconds()
        compound = lap["Compound"]
        row.compound = compound if isinstance(compound, str) else None
        row.data = resample(tel)
        saved += 1
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, default=None)
    parser.add_argument("--session", choices=["Q", "R"], default="Q")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if args.round:
            rounds = [args.round]
        else:
            rounds = db.scalars(
                select(Race.round).where(Race.season == args.season).order_by(Race.round)
            ).all()

        for rnd in rounds:
            print(f"{args.season} rodada {rnd} ({args.session})...")
            try:
                n = ingest_round(db, args.season, rnd, args.session)
                db.commit()
                print(f"  {n} voltas salvas")
            except Exception as exc:  # uma rodada com problema não derruba as outras
                db.rollback()
                print(f"  erro: {exc}")


if __name__ == "__main__":
    main()
