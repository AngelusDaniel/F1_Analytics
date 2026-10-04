import numpy as np

N_POINTS = 300


def resample(tel, n: int = N_POINTS) -> dict:
    """Reduz a telemetria de uma volta para `n` pontos igualmente espaçados em distância.

    `tel` é um DataFrame com as colunas: Distance, Time (timedelta), Speed,
    Throttle, Brake, nGear, X, Y.
    """
    dist = tel["Distance"].to_numpy(dtype=float)
    grid = np.linspace(0, dist.max(), n)

    time = tel["Time"].dt.total_seconds().to_numpy()
    time = time - time[0]  # começa em 0 no início da volta

    def interp(col: str) -> np.ndarray:
        return np.interp(grid, dist, tel[col].to_numpy(dtype=float))

    return {
        "distance": grid.round(1).tolist(),
        "time": np.interp(grid, dist, time).round(3).tolist(),
        "speed": interp("Speed").round(1).tolist(),
        "throttle": interp("Throttle").round(1).tolist(),
        "brake": (interp("Brake") > 0.5).astype(int).tolist(),
        "gear": interp("nGear").round().astype(int).tolist(),
        "x": interp("X").round().astype(int).tolist(),
        "y": interp("Y").round().astype(int).tolist(),
    }
