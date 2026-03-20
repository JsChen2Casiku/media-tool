from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from media_tool_core.configs.env_loader import load_project_env
load_project_env()

from media_tool_core.api import router
from media_tool_core.services.auth_service import get_authenticated_user

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="media-tool", version="1.0.0")
app.include_router(router, prefix="/api")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


@app.middleware("http")
async def protect_html_entrypoints(request: Request, call_next):
    if request.url.path == "/web/index.html":
        if not get_authenticated_user(request):
            return RedirectResponse(url="/login", status_code=302)
        return RedirectResponse(url="/", status_code=302)
    if request.url.path == "/web/login.html":
        if get_authenticated_user(request):
            return RedirectResponse(url="/", status_code=302)
        return RedirectResponse(url="/login", status_code=302)
    return await call_next(request)


def _render_html(filename: str) -> HTMLResponse:
    html = (WEB_DIR / filename).read_text(encoding="utf-8")
    return HTMLResponse(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/")
def index(request: Request):
    if not get_authenticated_user(request):
        return RedirectResponse(url="/login", status_code=302)
    return _render_html("index.html")


@app.get("/login")
def login_page(request: Request):
    if get_authenticated_user(request):
        return RedirectResponse(url="/", status_code=302)
    return _render_html("login.html")
