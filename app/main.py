from fastapi import FastAPI

from app.routers import drivers, races, compare


app = FastAPI(
    title="F1 Analytics API",
    description="Resultados históricos de F1, comparações e previsão de pódio.",
    version="0.1.0",
)

app.include_router(races.router)
app.include_router(compare.router)
app.include_router(drivers.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
