from fastapi import APIRouter, HTTPException

from media_tool_core.schemas import DownloadRequest, ExtractRequest, ParseRequest
from media_tool_core.services.media_service import download_media, extract_transcript, parse_media

router = APIRouter()


def _normalize_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ModuleNotFoundError):
        missing_name = getattr(exc, "name", None) or str(exc)
        return HTTPException(
            status_code=500,
            detail=f"服务端缺少依赖 {missing_name}，请检查本地 Python 环境或使用 Docker Compose 部署。",
        )
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
def health():
    return {"success": True, "message": "ok"}


@router.post("/parse")
def parse_route(payload: ParseRequest):
    try:
        return {"success": True, "data": parse_media(payload.text)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.post("/download")
def download_route(payload: DownloadRequest):
    try:
        return {"success": True, "data": download_media(payload)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.post("/extract")
def extract_route(payload: ExtractRequest):
    try:
        return {"success": True, "data": extract_transcript(payload)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc
