from datetime import date
from typing import Optional

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # ex: max_verstappen
    code: Mapped[Optional[str]] = mapped_column(String(3))  # ex: VER
    given_name: Mapped[str] = mapped_column(String)
    family_name: Mapped[str] = mapped_column(String)
    nationality: Mapped[Optional[str]] = mapped_column(String)


class Circuit(Base):
    __tablename__ = "circuits"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # ex: interlagos
    name: Mapped[str] = mapped_column(String)
    locality: Mapped[Optional[str]] = mapped_column(String)
    country: Mapped[Optional[str]] = mapped_column(String)


class Race(Base):
    __tablename__ = "races"
    __table_args__ = (UniqueConstraint("season", "round"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date)
    circuit_id: Mapped[str] = mapped_column(ForeignKey("circuits.id"))

    circuit: Mapped[Circuit] = relationship()
    results: Mapped[list["Result"]] = relationship(back_populates="race")


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("race_id", "driver_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    constructor_id: Mapped[str] = mapped_column(String)
    constructor_name: Mapped[str] = mapped_column(String)
    grid: Mapped[int] = mapped_column(Integer)  # 0 = largou dos boxes
    position: Mapped[Optional[int]] = mapped_column(Integer)  # None se não classificado
    points: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[Optional[str]] = mapped_column(String)
    laps: Mapped[Optional[int]] = mapped_column(Integer)

    race: Mapped[Race] = relationship(back_populates="results")
    driver: Mapped[Driver] = relationship()


class LapTelemetry(Base):
    """Volta mais rápida de um piloto em uma sessão (Q ou R), já reamostrada.

    `data` guarda listas de 300 pontos ao longo da volta:
    distance, time, speed, throttle, brake, gear, x, y.
    """

    __tablename__ = "lap_telemetry"
    __table_args__ = (UniqueConstraint("race_id", "driver_id", "session"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    session: Mapped[str] = mapped_column(String(2))  # "Q" ou "R"
    lap_time: Mapped[float] = mapped_column(Float)  # segundos
    compound: Mapped[Optional[str]] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)

    race: Mapped[Race] = relationship()
    driver: Mapped[Driver] = relationship()
