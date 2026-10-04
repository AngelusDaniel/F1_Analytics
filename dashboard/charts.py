import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# chaves = constructor_id da Jolpica
TEAM_COLORS = {
    "red_bull": "#3671C6", "mercedes": "#27F4D2", "ferrari": "#E8002D",
    "mclaren": "#FF8000", "aston_martin": "#229971", "alpine": "#FF87BC",
    "williams": "#64C4FF", "rb": "#6692FF", "alphatauri": "#5E8FAA",
    "toro_rosso": "#469BFF", "sauber": "#52E252", "alfa": "#C92D4B",
    "haas": "#B6BABD", "renault": "#FFF500", "racing_point": "#F596C8",
    "force_india": "#F596C8", "audi": "#F50537", "cadillac": "#AAAAAD",
}
FALLBACK = ["#1f77b4", "#ff7f0e"]


def lighten(hex_color: str, amount: float = 0.5) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def format_lap_time(seconds: float) -> str:
    m = int(seconds // 60)
    return f"{m}:{seconds - 60 * m:06.3f}"


def style_drivers(data: dict) -> list[dict]:
    """Junta a resposta da API com cor e traço de cada piloto."""
    drivers = []
    for i, d in enumerate(data["drivers"]):
        color = TEAM_COLORS.get(d.get("team"), FALLBACK[i])
        drivers.append(
            {**d, "color": color, "dash": "solid", "tel": data["telemetry"][d["code"]]}
        )
    # companheiros de equipe: o segundo ganha tom mais claro e linha tracejada
    if drivers[0]["color"] == drivers[1]["color"]:
        drivers[1]["color"] = lighten(drivers[1]["color"])
        drivers[1]["dash"] = "dash"
    return drivers


def telemetry_figure(drivers: list[dict], distance: list[float], delta: list[float]):
    a, b = drivers
    fig = make_subplots(
        rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.30, 0.16, 0.18, 0.12, 0.24],
        subplot_titles=(
            "Velocidade (km/h)",
            f"Delta (s): acima de 0, {b['code']} está atrás",
            "Acelerador (%)", "Freio", "Marcha",
        ),
    )
    for d in drivers:
        for row, key, shape in [(1, "speed", "linear"), (3, "throttle", "linear"),
                                (4, "brake", "hv"), (5, "gear", "hv")]:
            fig.add_trace(
                go.Scatter(
                    x=distance, y=d["tel"][key], name=d["code"], legendgroup=d["code"],
                    showlegend=(row == 1),
                    line=dict(color=d["color"], dash=d["dash"], width=2, shape=shape),
                ),
                row=row, col=1,
            )
    fig.add_trace(
        go.Scatter(x=distance, y=delta, name="delta", showlegend=False,
                   line=dict(color="#aaaaaa", width=2), fill="tozeroy"),
        row=2, col=1,
    )
    fig.update_layout(
        height=860, hovermode="x unified", margin=dict(t=60, b=40),
        legend=dict(orientation="h", y=1.06),
    )
    fig.update_xaxes(title_text="Distância (m)", row=5, col=1)
    return fig


def speed_map(driver: dict):
    tel = driver["tel"]
    fig = go.Figure(
        go.Scatter(
            x=tel["x"], y=tel["y"], mode="markers",
            marker=dict(color=tel["speed"], colorscale="RdYlGn", size=7,
                        colorbar=dict(title="km/h")),
            hovertemplate="%{marker.color:.0f} km/h<extra></extra>",
        )
    )
    fig.update_layout(
        height=520, margin=dict(t=20, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
    )
    return fig


def _state(tel: dict, t: float) -> dict:
    time = tel["time"]
    i = min(int(np.searchsorted(time, t)), len(time) - 1)
    return {
        "x": float(np.interp(t, time, tel["x"])),
        "y": float(np.interp(t, time, tel["y"])),
        "speed": float(np.interp(t, time, tel["speed"])),
        "throttle": float(np.interp(t, time, tel["throttle"])),
        "brake": tel["brake"][i],
        "gear": tel["gear"][i],
    }


def replay_figure(drivers, speed=1.0, step=1/30):
    """Animação da volta: os dois pilotos percorrendo a pista, sincronizados pelo tempo."""
    a, b = drivers
    t_end = max(a["tel"]["time"][-1], b["tel"]["time"][-1])
    times = np.arange(0, t_end + step, step)

    def traces(t: float):
        s = [_state(d["tel"], t) for d in drivers]
        dots = [
            go.Scatter(
                x=[s[i]["x"]], y=[s[i]["y"]], mode="markers+text",
                text=[f"{d['code']} {s[i]['speed']:.0f} km/h · {s[i]['gear']}ª"],
                textposition="top center", textfont=dict(color=d["color"]),
                marker=dict(size=15, color=d["color"], line=dict(color="white", width=1)),
            )
            for i, d in enumerate(drivers)
        ]
        colors = [a["color"], b["color"]]
        codes = [a["code"], b["code"]]
        throttle = go.Bar(x=codes, y=[s[0]["throttle"], s[1]["throttle"]], marker_color=colors)
        brake = go.Bar(x=codes, y=[100 * s[0]["brake"], 100 * s[1]["brake"]], marker_color=colors)
        gear = go.Bar(
            x=codes,
            y=[s[0]["gear"], s[1]["gear"]],
            marker_color=colors,
        )
        return dots + [throttle, brake, gear]

    fig = make_subplots(
    rows=1, cols=4, column_widths=[0.5, 0.17, 0.17, 0.16],
    subplot_titles=("Pista", "Acelerador (%)", "Freio", "Marcha"),
    )
    fig.add_trace(
        go.Scatter(x=a["tel"]["x"], y=a["tel"]["y"], mode="lines",
                   line=dict(color="#555555", width=6), hoverinfo="skip"),
        row=1, col=1,
    )
    first = traces(0.0)
    for tr, col in zip(first, [1, 1, 2, 3, 4]):
        fig.add_trace(tr, row=1, col=col)

    fig.frames = [go.Frame(data=traces(float(t)), traces=[1, 2, 3, 4, 5], name=str(i))
              for i, t in enumerate(times)]

    frame_ms = int(step * 1000 / speed)
    fig.update_layout(
        height=560, showlegend=False, margin=dict(t=50, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
        yaxis2=dict(range=[0, 100]), yaxis3=dict(range=[0, 100]),
        yaxis4=dict(range=[0, 8], dtick=1),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.0, y=-0.02, xanchor="left", yanchor="top",
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[None, dict(
                        frame=dict(duration=frame_ms, redraw=False),
                        transition=dict(duration=frame_ms, easing="linear"),
                        fromcurrent=True,
                        mode="immediate",
                    )],
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[[None], dict(
                        frame=dict(duration=0, redraw=False),
                        transition=dict(duration=0),
                        mode="immediate",
                    )],
                ),
            ],
        )],
        sliders=[dict(
            x=0.12, len=0.88, y=-0.02, currentvalue=dict(prefix="t = ", suffix=" s"),
            steps=[dict(method="animate",
                        label=f"{t:.0f}" if i % 4 == 0 else "",
                        args=[[str(i)], dict(mode="immediate",
                                             frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))])
                      for i, t in enumerate(times) if i % 6 == 0],
        )],
    )
    return fig
