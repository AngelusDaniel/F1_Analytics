"""Formato das respostas da API (Pydantic).

Separar schemas de models evita expor o banco diretamente:
você controla exatamente o que sai no JSON.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lê objetos do SQLAlchemy


class CircuitOut(OrmModel):
    id: str
    name: str
    locality: Optional[str]
    country: Optional[str]


class DriverOut(OrmModel):
    id: str
    code: Optional[str]
    given_name: str
    family_name: str
    nationality: Optional[str]


class RaceOut(OrmModel):
    season: int
    round: int
    name: str
    date: date
    circuit: CircuitOut


class ResultOut(OrmModel):
    position: Optional[int]
    grid: int
    points: float
    status: Optional[str]
    laps: Optional[int]
    constructor_name: str
    driver: DriverOut


class RaceDetail(RaceOut):
    results: list[ResultOut]


class DriverResultOut(BaseModel):
    season: int
    round: int
    race_name: str
    grid: int
    position: Optional[int]
    points: float
    constructor_name: str
    status: Optional[str]


class LapSummary(BaseModel):
    code: str
    name: str
    lap_time: float  # segundos
    compound: Optional[str]
    team: Optional[str]  # constructor_id, usado para a cor


class Channels(BaseModel):
    speed: list[float]
    throttle: list[float]
    brake: list[int]
    gear: list[int]
    time: list[float]  # segundos desde o início da volta
    x: list[int]
    y: list[int]


class Track(BaseModel):
    x: list[int]
    y: list[int]


class CompareOut(BaseModel):
    season: int
    round: int
    race_name: str
    session: str
    drivers: list[LapSummary]
    distance: list[float]  # metros, base do piloto 1
    telemetry: dict[str, Channels]  # chave = código do piloto
    delta: list[float]  # tempo do piloto 2 menos o do piloto 1; positivo = piloto 2 atrás
    track: Track  # traçado da pista (coordenadas do piloto 1)
