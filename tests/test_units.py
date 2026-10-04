import numpy as np
import pandas as pd

from app.db import normalize_url
from scripts.resample import resample


def _fake_lap(n: int = 50) -> pd.DataFrame:
    return pd.DataFrame({
        "Distance": np.linspace(0, 5000, n),
        "Time": pd.to_timedelta(np.linspace(0, 80, n), unit="s"),
        "Speed": np.linspace(100, 300, n),
        "Throttle": np.full(n, 100.0),
        "Brake": np.r_[np.zeros(n // 2, bool), np.ones(n - n // 2, bool)],
        "nGear": np.full(n, 5),
        "X": np.linspace(0, 1000, n),
        "Y": np.linspace(0, 500, n),
    })


def test_resample_returns_fixed_size_channels():
    out = resample(_fake_lap(), n=300)
    assert set(out) == {"distance", "time", "speed", "throttle", "brake", "gear", "x", "y"}
    assert all(len(v) == 300 for v in out.values())


def test_resample_time_starts_at_zero_and_ends_at_lap_time():
    out = resample(_fake_lap())
    assert out["time"][0] == 0
    assert out["time"][-1] == 80.0


def test_resample_brake_is_binary():
    out = resample(_fake_lap())
    assert set(out["brake"]) <= {0, 1}
    assert out["brake"][0] == 0 and out["brake"][-1] == 1


def test_normalize_url_for_psycopg3():
    assert normalize_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalize_url("postgresql://u:p@host/db?sslmode=require") == \
        "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert normalize_url("sqlite://") == "sqlite://"
