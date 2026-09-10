from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.health import router as health_router


app = FastAPI(
    title="Eerly Workspace AI",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(agent_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}