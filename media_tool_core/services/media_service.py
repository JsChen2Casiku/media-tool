import mimetypes
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse

import requests
from fastapi.responses import StreamingResponse

from media_tool_core.configs.general_constants import DOMAIN_TO_PLATFORM, PROJECT_ROOT, get_platform_label
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloader_factory import DownloaderFactory
from media_tool_core.schemas import DownloadRequest, ExtractRequest
from media_tool_core.services.transcription_service import (
    TranscriptionConfig,
    TranscriptionResult,
    create_transcriber,
)
from media_tool_core.utils.web_fetcher import UrlParser, WebFetcher

logger = get_logger(__name__)
REQUEST_TIMEOUT = int(os.getenv("MEDIA_TOOL_REQUEST_TIMEOUT", "30"))
STORAGE_ROOT = Path(os.getenv("MEDIA_TOOL_STORAGE_ROOT", str(Path(PROJECT_ROOT) / "storage")))
TEMP_ROOT = STORAGE_ROOT / "temp"
EXPORT_ROOT = STORAGE_ROOT / "exports"

for path in [STORAGE_ROOT, TEMP_ROOT, EXPORT_ROOT]:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class ParsedMedia:
    video_id: Optional[str]
    platform: str
    title: Optional[str]
    source_url: str
    redirect_url: str
    real_url: str
    video_url: Optional[str]
    audio_url: Optional[str]
    cover_url: Optional[str]
    author: Optional[dict]
    image_list: list[str]

    @property
    def is_image_post(self) -> bool:
        return bool(self.image_list) and not self.video_url

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["is_image_post"] = self.is_image_post
        return payload


@dataclass
class ResolvedAsset:
    url: str
    filename: str
    referer: str
    headers: Optional[dict]


def parse_media(text: str) -> dict:
    parsed, _ = _resolve_media_with_downloader(text)
    return parsed.to_dict()


def download_media(payload: DownloadRequest) -> dict:
    parsed, downloader = _resolve_media_with_downloader(payload.text)
    export_dir = _prepare_export_dir(payload.output_dir, parsed.video_id, parsed.title)
    saved_files = {"video": None, "cover": None, "images": []}

    if payload.save_video and parsed.video_url:
        saved_files["video"] = _download_url(
            parsed.video_url,
            export_dir,
            prefix="video",
            fallback_extension=".mp4",
            headers=getattr(downloader, "headers", None),
            referer=parsed.real_url,
        )

    if payload.save_cover and parsed.cover_url:
        saved_files["cover"] = _download_url(
            parsed.cover_url,
            export_dir,
            prefix="cover",
            fallback_extension=".jpg",
            headers=getattr(downloader, "headers", None),
            referer=parsed.real_url,
        )

    if payload.save_images and parsed.image_list:
        for index, image_url in enumerate(parsed.image_list, start=1):
            saved_files["images"].append(
                _download_url(
                    image_url,
                    export_dir,
                    prefix=f"image_{index:02d}",
                    fallback_extension=".jpg",
                    headers=getattr(downloader, "headers", None),
                    referer=parsed.real_url,
                )
            )

    return {
        "media": parsed.to_dict(),
        "output_dir": str(export_dir),
        "saved_files": saved_files,
    }


def extract_transcript(payload: ExtractRequest) -> dict:
    parsed, downloader = _resolve_media_with_downloader(payload.text)
    source_url = parsed.audio_url or parsed.video_url
    if not source_url:
        raise ValueError("当前链接没有可转写的音频或视频地址，通常说明这是图集内容。")

    config = TranscriptionConfig.from_values(
        transcription_base_url=payload.transcription_base_url,
        transcription_task=payload.transcription_task,
        transcription_language=payload.transcription_language,
        transcription_timeout=payload.transcription_timeout,
        transcription_encode=payload.transcription_encode,
        transcription_word_timestamps=payload.transcription_word_timestamps,
        transcription_vad_filter=payload.transcription_vad_filter,
    )
    transcriber = create_transcriber(config)

    export_dir = _prepare_export_dir(payload.output_dir, parsed.video_id, parsed.title)
    temp_dir = TEMP_ROOT / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)

    source_extension = _guess_extension(source_url, ".mp3" if parsed.audio_url else ".mp4")
    source_path = temp_dir / f"source{source_extension}"

    try:
        _download_to_path(
            source_url,
            source_path,
            headers=getattr(downloader, "headers", None),
            referer=parsed.real_url,
        )

        transcription_result = transcriber.transcribe(source_path)
        transcript_text = transcription_result.text.strip()

        saved_files = {"transcript": None, "video": None, "cover": None, "images": []}

        if payload.save_transcript:
            transcript_path = export_dir / "transcript.md"
            transcript_path.write_text(
                _build_transcript_markdown(parsed, transcription_result, config),
                encoding="utf-8",
            )
            saved_files["transcript"] = str(transcript_path)

        if payload.save_video and parsed.video_url:
            saved_files["video"] = _download_url(
                parsed.video_url,
                export_dir,
                prefix="video",
                fallback_extension=".mp4",
                headers=getattr(downloader, "headers", None),
                referer=parsed.real_url,
            )

        if payload.save_cover and parsed.cover_url:
            saved_files["cover"] = _download_url(
                parsed.cover_url,
                export_dir,
                prefix="cover",
                fallback_extension=".jpg",
                headers=getattr(downloader, "headers", None),
                referer=parsed.real_url,
            )

        if payload.save_images and parsed.image_list:
            for index, image_url in enumerate(parsed.image_list, start=1):
                saved_files["images"].append(
                    _download_url(
                        image_url,
                        export_dir,
                        prefix=f"image_{index:02d}",
                        fallback_extension=".jpg",
                        headers=getattr(downloader, "headers", None),
                        referer=parsed.real_url,
                    )
                )

        return {
            "media": parsed.to_dict(),
            "transcript": transcript_text,
            "output_dir": str(export_dir),
            "saved_files": saved_files,
            "transcription": _build_transcription_metadata(config, transcription_result),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def stream_media_asset(
    text: str,
    kind: str,
    index: int | None = None,
    disposition: str = "inline",
    range_header: str | None = None,
):
    parsed, downloader = _resolve_media_with_downloader(text)
    asset = _resolve_asset(parsed, downloader, kind, index)

    request_headers = _build_headers(asset.headers, asset.referer)
    if range_header:
        request_headers["Range"] = range_header

    upstream = requests.get(
        asset.url,
        headers=request_headers,
        stream=True,
        allow_redirects=True,
        timeout=REQUEST_TIMEOUT,
    )
    upstream.raise_for_status()

    media_type = upstream.headers.get("Content-Type") or _guess_media_type(asset.filename)
    response_headers = {
        "Content-Disposition": _build_content_disposition(asset.filename, disposition),
        "Cache-Control": "no-store",
    }

    for header_name in ["Accept-Ranges", "Content-Length", "Content-Range", "ETag", "Last-Modified"]:
        header_value = upstream.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    def body_iter():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return StreamingResponse(
        body_iter(),
        status_code=upstream.status_code,
        media_type=media_type,
        headers=response_headers,
    )


def _resolve_media_with_downloader(text: str):
    share_url = UrlParser.get_url(text or "")
    if not share_url:
        raise ValueError("未从输入文本中提取到有效链接。")

    redirect_url = WebFetcher.fetch_redirect_url(share_url)
    if not redirect_url:
        raise ValueError("无法解析分享链接，请确认链接有效。")

    real_url = UrlParser.extract_video_address(redirect_url)
    platform_key = DOMAIN_TO_PLATFORM.get(UrlParser.get_domain(redirect_url))
    if not platform_key:
        raise ValueError(f"暂不支持解析该链接: {redirect_url}")

    downloader = DownloaderFactory.create_downloader(platform_key, real_url)
    content = _fetch_with_retry(downloader, platform_key)
    if not content["video_url"] and not content["image_list"]:
        raise ValueError(f"{get_platform_label(platform_key)} 内容解析失败，未获取到视频或图集地址。")

    parsed = ParsedMedia(
        video_id=UrlParser.get_video_id(redirect_url),
        platform=get_platform_label(platform_key),
        title=content["title"],
        source_url=share_url,
        redirect_url=redirect_url,
        real_url=real_url,
        video_url=UrlParser.convert_to_https(content["video_url"]),
        audio_url=UrlParser.convert_to_https(content.get("audio_url")),
        cover_url=UrlParser.convert_to_https(content["cover_url"]),
        author=content["author"],
        image_list=[UrlParser.convert_to_https(item) for item in content["image_list"]],
    )
    return parsed, downloader


def _resolve_asset(parsed: ParsedMedia, downloader, kind: str, index: int | None = None) -> ResolvedAsset:
    normalized_kind = (kind or "").strip().lower()
    headers = getattr(downloader, "headers", None)
    base_name = _safe_name(parsed.title or parsed.video_id or "media")

    if normalized_kind == "video":
        if not parsed.video_url:
            raise ValueError("当前内容没有可预览或下载的视频地址。")
        ext = _guess_extension(parsed.video_url, ".mp4")
        return ResolvedAsset(parsed.video_url, f"{base_name}_video{ext}", parsed.real_url, headers)

    if normalized_kind == "audio":
        if not parsed.audio_url:
            raise ValueError("当前内容没有可预览或下载的音频地址。")
        ext = _guess_extension(parsed.audio_url, ".mp3")
        return ResolvedAsset(parsed.audio_url, f"{base_name}_audio{ext}", parsed.real_url, headers)

    if normalized_kind == "cover":
        if not parsed.cover_url:
            raise ValueError("当前内容没有可预览或下载的封面地址。")
        ext = _guess_extension(parsed.cover_url, ".jpg")
        return ResolvedAsset(parsed.cover_url, f"{base_name}_cover{ext}", parsed.real_url, headers)

    if normalized_kind == "image":
        if index is None:
            raise ValueError("图集预览或下载需要提供 index 参数。")
        if index < 0 or index >= len(parsed.image_list):
            raise ValueError("图集索引超出范围。")
        image_url = parsed.image_list[index]
        ext = _guess_extension(image_url, ".jpg")
        return ResolvedAsset(image_url, f"{base_name}_image_{index + 1:02d}{ext}", parsed.real_url, headers)

    raise ValueError(f"不支持的资源类型: {kind}")


def _fetch_with_retry(downloader, platform_key: str) -> dict:
    max_attempts = 3 if platform_key == "xiaohongshu" else 1
    result = None
    for _ in range(max_attempts):
        result = {
            "title": downloader.get_title_content(),
            "video_url": downloader.get_real_video_url(),
            "cover_url": downloader.get_cover_photo_url(),
            "author": _safe_execute(downloader.get_author_info),
            "image_list": _safe_execute(downloader.get_image_list, []),
            "audio_url": _safe_execute(downloader.get_audio_url),
        }
        if result["video_url"] or result["image_list"]:
            return result
    return result or {}


def _safe_execute(func, default=None):
    try:
        return func()
    except Exception:
        return default


def _prepare_export_dir(output_dir: Optional[str], video_id: Optional[str], title: Optional[str]) -> Path:
    base_dir = Path(output_dir) if output_dir else EXPORT_ROOT
    folder_name = _safe_name(title or video_id or datetime.now().strftime("%Y%m%d_%H%M%S"))
    export_dir = base_dir / folder_name
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned[:80] or "media"


def _build_headers(
    custom_headers: Optional[dict] = None,
    referer: Optional[str] = None,
    request_url: Optional[str] = None,
) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if custom_headers:
        headers.update(custom_headers)
    if referer and "Referer" not in headers:
        headers["Referer"] = referer
    if referer and "Origin" not in headers:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
    if _is_douyin_cdn_request(request_url, referer):
        headers.setdefault("Range", "bytes=0-")
        headers.setdefault("Sec-Fetch-Site", "cross-site")
        headers.setdefault("Sec-Fetch-Mode", "no-cors")
        headers.setdefault("Sec-Fetch-Dest", "video")
        headers.setdefault("Accept-Encoding", "identity;q=1, *;q=0")
    return headers


def _download_url(
    url: str,
    output_dir: Path,
    prefix: str,
    fallback_extension: str,
    headers: Optional[dict] = None,
    referer: Optional[str] = None,
) -> str:
    extension = _guess_extension(url, fallback_extension)
    target_path = output_dir / f"{prefix}{extension}"
    _download_to_path(url, target_path, headers=headers, referer=referer)
    return str(target_path)


def _download_to_path(url: str, target_path: Path, headers: Optional[dict] = None, referer: Optional[str] = None) -> None:
    request_headers = _build_headers(headers, referer, url)
    response = requests.get(
        url,
        headers=request_headers,
        stream=True,
        allow_redirects=True,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code == 403 and _is_douyin_cdn_request(url, referer):
        response.close()
        retry_headers = dict(request_headers)
        retry_headers["Range"] = "bytes=0-"
        retry_headers["Accept"] = "video/webm,video/ogg,video/*;q=0.9,*/*;q=0.8"
        response = requests.get(
            url,
            headers=retry_headers,
            stream=True,
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT,
        )
    response.raise_for_status()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as file_obj:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_obj.write(chunk)


def _is_douyin_cdn_request(request_url: Optional[str], referer: Optional[str]) -> bool:
    haystacks = [request_url or "", referer or ""]
    keywords = ("douyinvod.com", "douyin.com", "iesdouyin.com", "byteimg.com")
    return any(keyword in text for text in haystacks for keyword in keywords)


def _guess_extension(url: str, fallback_extension: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix and len(suffix) <= 8:
        return suffix
    return fallback_extension


def _guess_media_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _build_content_disposition(filename: str, disposition: str) -> str:
    resolved_disposition = "attachment" if disposition == "attachment" else "inline"
    return f"{resolved_disposition}; filename*=UTF-8''{quote(filename)}"


def _build_transcription_metadata(config: TranscriptionConfig, result: TranscriptionResult) -> dict:
    return {
        "provider": "whisper-asr-webservice",
        "base_url": config.base_url,
        "endpoint": config.endpoint,
        "task": config.task,
        "language": config.language,
        "detected_language": result.language,
        "encode": config.encode,
        "word_timestamps": config.word_timestamps,
        "vad_filter": config.vad_filter,
        "cleanup": "转写完成后自动删除临时下载文件",
        "segment_count": len(result.segments),
    }


def _build_transcript_markdown(parsed: ParsedMedia, result: TranscriptionResult, config: TranscriptionConfig) -> str:
    lines = [
        f"# {parsed.title or '未命名视频'}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 平台 | {parsed.platform} |",
        f"| 视频 ID | `{parsed.video_id or ''}` |",
        f"| 原始链接 | {parsed.source_url} |",
        f"| 解析时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| 转写服务 | `{config.base_url}` |",
        f"| 转写任务 | `{config.task}` |",
        f"| 指定语言 | `{config.language or 'auto'}` |",
        f"| 检测语言 | `{result.language or 'unknown'}` |",
        "",
        "## 文案",
        "",
        result.text.strip(),
        "",
    ]
    return "\n".join(lines)
