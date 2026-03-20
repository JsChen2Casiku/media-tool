from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from media_tool_core.configs.env_loader import load_project_env
load_project_env()

from media_tool_core.api import router

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="media-tool", version="1.0.0")
app.include_router(router, prefix="/api")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


@app.get("/")
def index():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
