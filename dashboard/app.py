"""Dashboard Streamlit: consome apenas a API (nunca o FastF1 nem o banco).

Rodar (com a API no ar):  streamlit run dashboard/app.py
"""
import os
from datetime import date

import httpx
import streamlit as st
from charts import (format_lap_time, replay_figure, speed_map, style_drivers,
                    telemetry_figure)

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="F1 Analytics", page_icon="🏎️", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def api_get(path: str, **params):
    resp = httpx.get(f"{API_URL}{path}", params=params, timeout=90)
    resp.raise_for_status()
    return resp.json()


st.title("🏎️ F1 Analytics")

# ---- seleção ----
season = st.sidebar.selectbox("Temporada", list(range(date.today().year, 2017, -1)))
try:
    with st.spinner("Conectando à API (se estiver dormindo, pode levar cerca de 1 minuto)..."):
        races = sorted(api_get("/races", season=season, limit=100), key=lambda r: r["round"])
except httpx.HTTPError:
    st.error(f"Não consegui falar com a API em {API_URL}. Ela está rodando?")
    st.stop()
if not races:
    st.warning("Sem corridas no banco para essa temporada.")
    st.stop()

race = st.sidebar.selectbox("Corrida", races, format_func=lambda r: f"R{r['round']} · {r['name']}")
session = st.sidebar.radio(
    "Sessão", ["Q", "R"], horizontal=True,
    format_func={"Q": "Qualificação", "R": "Corrida"}.get,
)

codes = api_get("/compare/available", season=season, round=race["round"], session=session)
if len(codes) < 2:
    st.warning("Sem telemetria ingerida para essa sessão. Rode scripts.ingest_telemetry.")
    st.stop()

d1 = st.sidebar.selectbox("Piloto 1", codes, index=0)
d2 = st.sidebar.selectbox("Piloto 2", [c for c in codes if c != d1], index=0)

try:
    data = api_get("/compare", season=season, round=race["round"], d1=d1, d2=d2, session=session)
except httpx.HTTPError as exc:
    st.error(f"Erro ao buscar a comparação: {exc}")
    st.stop()

drivers = style_drivers(data)
a, b = drivers

# ---- resumo ----
st.subheader(f"{data['race_name']} {data['season']}")
c1, c2, c3 = st.columns(3)
for col, d in zip((c1, c2), drivers):
    col.metric(d["name"], format_lap_time(d["lap_time"]), d["compound"] or "pneu n/d")
gap = b["lap_time"] - a["lap_time"]
c3.metric("Diferença", f"{abs(gap):.3f} s", f"{a['code'] if gap > 0 else b['code']} mais rápido",
          delta_color="off")

# ---- abas ----
tab_tel, tab_map, tab_replay = st.tabs(["Telemetria", "Mapa de velocidade", "Replay"])

with tab_tel:
    st.plotly_chart(telemetry_figure(drivers, data["distance"], data["delta"]))

with tab_map:
    who = st.radio("Velocidade de", [a["code"], b["code"]], horizontal=True)
    st.plotly_chart(speed_map(a if who == a["code"] else b))

with tab_replay:
    rate = st.radio("Velocidade da animação", [0.5, 1.0, 2.0], index=1, horizontal=True,
                    format_func=lambda v: f"{v}x")
    st.plotly_chart(replay_figure(drivers, speed=rate))
    st.caption("Os dois pilotos são sincronizados pelo tempo desde o início da volta.")
