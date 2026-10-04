from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, Circuit, Driver, LapTelemetry, Race, Result


def _telemetry(times: list[float]) -> dict:
    n = len(times)
    return {
        "distance": [0.0, 100.0, 200.0, 300.0, 400.0],
        "time": times,
        "speed": [100.0, 200.0, 250.0, 150.0, 300.0],
        "throttle": [0.0, 100.0, 100.0, 20.0, 100.0],
        "brake": [0, 0, 0, 1, 0],
        "gear": [2, 5, 7, 3, 8],
        "x": list(range(n)),
        "y": list(range(n)),
    }


def seed(db):
    db.add(Circuit(id="albert_park", name="Albert Park", locality="Melbourne", country="Australia"))
    r23 = Race(season=2023, round=1, name="Australian Grand Prix",
               date=date(2023, 3, 5), circuit_id="albert_park")
    r22 = Race(season=2022, round=1, name="Bahrain Grand Prix",
               date=date(2022, 3, 20), circuit_id="albert_park")
    ver = Driver(id="max_verstappen", code="VER", given_name="Max",
                 family_name="Verstappen", nationality="Dutch")
    per = Driver(id="perez", code="PER", given_name="Sergio",
                 family_name="Perez", nationality="Mexican")
    ham = Driver(id="hamilton", code="HAM", given_name="Lewis",
                 family_name="Hamilton", nationality="British")
    db.add_all([r23, r22, ver, per, ham])
    db.flush()

    def result(driver, grid, position, status):
        return Result(race_id=r23.id, driver_id=driver.id, constructor_id="red_bull",
                      constructor_name="Red Bull", grid=grid, position=position,
                      points=25.0 if position == 1 else 0.0, status=status, laps=58)

    db.add_all([
        result(per, 2, None, "Retired"),   # abandono: position None
        result(ham, 3, 2, "Finished"),
        result(ver, 1, 1, "Finished"),
    ])
    db.add_all([
        LapTelemetry(race_id=r23.id, driver_id=ver.id, session="Q", lap_time=80.0,
                     compound="SOFT", data=_telemetry([0, 20, 40, 60, 80])),
        LapTelemetry(race_id=r23.id, driver_id=per.id, session="Q", lap_time=82.0,
                     compound="SOFT", data=_telemetry([0, 20.5, 41, 61.5, 82])),
    ])
    db.commit()


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        seed(db)

    def override_get_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
