from fastapi import APIRouter, HTTPException, Path, Query, Request

from media_tool_core.schemas import DownloadRequest, ExtractRequest, ParseRequest
from media_tool_core.services.job_service import JobNotFoundError, create_extract_job, get_job
from media_tool_core.services.media_service import download_media, parse_media, stream_media_asset

router = APIRouter()


def _normalize_exception(exc: Exception) -> HTTPException:
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
        return {"success": True, "data": create_extract_job(payload)}
    except Exception as exc:
        raise _normalize_exception(exc) from exc


@router.get("/jobs/{job_id}")
def job_route(job_id: str = Path(..., description="异步转写任务 ID")):
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
