"""Ingere resultados de corridas da Jolpica-F1 no PostgreSQL.

Uso:
    python -m scripts.ingest --from 2018 --to 2025

É idempotente: pode rodar várias vezes sem duplicar dados.
"""
import argparse
import time
from datetime import date

import httpx
from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Base, Circuit, Driver, Race, Result

BASE_URL = "https://api.jolpi.ca/ergast/f1"
PAGE_SIZE = 100


def fetch_season(client: httpx.Client, season: int):
    """Percorre as páginas da API e devolve as corridas da temporada.

    A paginação é por linhas de resultado, então a mesma corrida pode
    aparecer em duas páginas com resultados diferentes. O upsert cobre isso.
    """
    offset = 0
    while True:
        resp = client.get(
            f"{BASE_URL}/{season}/results.json",
            params={"limit": PAGE_SIZE, "offset": offset},
        )
        resp.raise_for_status()
        data = resp.json()["MRData"]
        yield from data["RaceTable"]["Races"]
        offset += PAGE_SIZE
        if offset >= int(data["total"]):
            break
        time.sleep(0.5)  # respeita o limite de requisições da API


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_race(session, raw: dict) -> int:
    c = raw["Circuit"]
    session.merge(
        Circuit(
            id=c["circuitId"],
            name=c["circuitName"],
            locality=c["Location"].get("locality"),
            country=c["Location"].get("country"),
        )
    )
    session.flush()

    season, rnd = int(raw["season"]), int(raw["round"])
    race = session.scalar(
        select(Race).where(Race.season == season, Race.round == rnd)
    )
    if race is None:
        race = Race(season=season, round=rnd)
        session.add(race)
    race.name = raw["raceName"]
    race.date = date.fromisoformat(raw["date"])
    race.circuit_id = c["circuitId"]
    session.flush()  # garante race.id

    for r in raw["Results"]:
        d = r["Driver"]
        session.merge(
            Driver(
                id=d["driverId"],
                code=d.get("code"),
                given_name=d["givenName"],
                family_name=d["familyName"],
                nationality=d.get("nationality"),
            )
        )
        session.flush()

        result = session.scalar(
            select(Result).where(
                Result.race_id == race.id, Result.driver_id == d["driverId"]
            )
        )
        if result is None:
            result = Result(race_id=race.id, driver_id=d["driverId"])
            session.add(result)
        result.constructor_id = r["Constructor"]["constructorId"]
        result.constructor_name = r["Constructor"]["name"]
        result.grid = to_int(r["grid"]) or 0
        # "R", "D", "W" (abandono, desqualificado...) viram None
        result.position = to_int(r["position"]) if r["positionText"].isdigit() else None
        result.points = float(r["points"])
        result.status = r.get("status")
        result.laps = to_int(r.get("laps"))
    return len(raw["Results"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", type=int, default=2018)
    parser.add_argument("--to", dest="end", type=int, default=date.today().year)
    args = parser.parse_args()

    Base.metadata.create_all(engine)

    with httpx.Client(timeout=30) as client, SessionLocal() as session:
        for season in range(args.start, args.end + 1):
            count = 0
            for raw in fetch_season(client, season):
                count += save_race(session, raw)
            session.commit()
            print(f"{season}: {count} resultados processados")


if __name__ == "__main__":
    main()
