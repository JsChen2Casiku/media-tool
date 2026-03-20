from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from media_tool_core.schemas import (
    ChangePasswordRequest,
    DownloadRequest,
    ExtractRequest,
    LoginRequest,
    ParseRequest,
)
from media_tool_core.services.auth_service import (
    SESSION_COOKIE_NAME,
    create_session,
    get_auth_username,
    get_cookie_secure,
    get_session_max_age,
    require_auth,
    revoke_session,
    update_password,
    validate_login,
)
from media_tool_core.services.job_service import JobNotFoundError, create_extract_job, get_job
from media_tool_core.services.media_service import download_media, parse_media, stream_media_asset

router = APIRouter()


def _normalize_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, JobNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ModuleNotFoundError):
        missing_name = getattr(exc, "name", None) or str(exc)
        return HTTPException(
            status_code=500,
            detail=f"服务端缺少依赖 {missing_name}，请检查本地 Python 环境或重新构建 Docker 镜像。",
        )
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
def health():
    return {"success": True, "message": "ok"}


@router.post("/auth/login")
def login_route(payload: LoginRequest):
    try:
        validate_login(payload.username.strip(), payload.password)
        token = create_session(payload.username.strip())
        response = JSONResponse(
            {
                "success": True,
                "data": {
                    "username": payload.username.strip(),
                    "message": "登录成功。",
                },
            }
        )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            max_age=get_session_max_age(),
            httponly=True,
            samesite="lax",
            secure=get_cookie_secure(),
            path="/",
        )
        return response
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.post("/auth/logout")
def logout_route(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    revoke_session(token)
    response = JSONResponse({"success": True, "data": {"message": "已退出登录。"}})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/auth/me")
def auth_me_route(request: Request):
    username = require_auth(request)
    return {"success": True, "data": {"username": username}}


@router.post("/auth/change-password")
def change_password_route(request: Request, payload: ChangePasswordRequest):
    try:
        username = require_auth(request)
        update_password(payload.current_password, payload.new_password, payload.confirm_password)
        token = create_session(username)
        response = JSONResponse(
            {
                "success": True,
                "data": {
                    "username": username,
                    "message": "密码修改成功。",
                },
            }
        )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            max_age=get_session_max_age(),
            httponly=True,
            samesite="lax",
            secure=get_cookie_secure(),
            path="/",
        )
        return response
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.get("/auth/config")
def auth_config_route(request: Request):
    require_auth(request)
    return {
        "success": True,
        "data": {
            "username": get_auth_username(),
        },
    }


@router.post("/parse")
def parse_route(request: Request, payload: ParseRequest):
    require_auth(request)
    try:
        return {"success": True, "data": parse_media(payload.text)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.post("/download")
def download_route(request: Request, payload: DownloadRequest):
    require_auth(request)
    try:
        return {"success": True, "data": download_media(payload)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.post("/extract")
def extract_route(request: Request, payload: ExtractRequest):
    require_auth(request)
    try:
        return {"success": True, "data": create_extract_job(payload)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.get("/jobs/{job_id}")
def job_route(request: Request, job_id: str = Path(..., description="异步转写任务 ID")):
    require_auth(request)
    try:
        return {"success": True, "data": get_job(job_id)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.get("/asset")
def asset_route(
    request: Request,
    text: str = Query(..., description="原始分享文案或链接"),
    kind: str = Query(..., description="资源类型，支持 video、audio、cover、image"),
    index: int | None = Query(default=None, description="图集索引，仅 kind=image 时使用"),
    disposition: str = Query(default="inline", description="inline 或 attachment"),
):
    require_auth(request)
    try:
        return stream_media_asset(
            text=text,
            kind=kind,
            index=index,
            disposition=disposition,
            range_header=request.headers.get("range"),
        )
    except Exception as exc:
        raise _normalize_exception(exc) from exc
