import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from media_tool_core.configs.general_constants import DOMAIN_TO_PLATFORM, PROJECT_ROOT, get_platform_label
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloader_factory import DownloaderFactory
from media_tool_core.schemas import DownloadRequest, ExtractRequest
from media_tool_core.services.transcription_service import OpenAICompatibleTranscriber, TranscriptionConfig
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
    if not parsed.video_url:
        raise ValueError("当前链接没有可转写的视频地址，通常说明这是一条纯图集内容。")

    config = TranscriptionConfig.from_values(payload.api_base, payload.api_key, payload.model)
    _ensure_ffmpeg_available()

    export_dir = _prepare_export_dir(payload.output_dir, parsed.video_id, parsed.title)
    temp_dir = TEMP_ROOT / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)

    video_path = temp_dir / "source.mp4"
    audio_path = temp_dir / "source.mp3"

    try:
        _download_to_path(
            parsed.video_url,
            video_path,
            headers=getattr(downloader, "headers", None),
            referer=parsed.real_url,
        )
        _extract_audio(video_path, audio_path)

        transcriber = OpenAICompatibleTranscriber(config)
        transcript_text = transcriber.transcribe(audio_path)

        saved_files = {"transcript": None, "video": None, "cover": None, "images": []}

        if payload.save_transcript:
            transcript_path = export_dir / "transcript.md"
            transcript_path.write_text(_build_transcript_markdown(parsed, transcript_text, config), encoding="utf-8")
            saved_files["transcript"] = str(transcript_path)

        if payload.save_video:
            saved_video = export_dir / f"{_safe_name(parsed.title or parsed.video_id or 'video')}.mp4"
            shutil.copy2(video_path, saved_video)
            saved_files["video"] = str(saved_video)

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
            "transcription": {
                "api_base": config.api_base,
                "model": config.model,
            },
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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


def _build_headers(custom_headers: Optional[dict] = None, referer: Optional[str] = None) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if custom_headers:
        headers.update(custom_headers)
    if referer and "Referer" not in headers:
        parsed = urlparse(referer)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
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
    response = requests.get(
        url,
        headers=_build_headers(headers, referer),
        stream=True,
        allow_redirects=True,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    with open(target_path, "wb") as file_obj:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_obj.write(chunk)


def _guess_extension(url: str, fallback_extension: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix and len(suffix) <= 8:
        return suffix
    return fallback_extension


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg"):
        return
    raise ValueError("未检测到 ffmpeg 可执行文件，请先安装 ffmpeg 并加入 PATH。")


def _extract_audio(video_path: Path, audio_path: Path) -> None:
    import ffmpeg

    (
        ffmpeg.input(str(video_path))
        .output(str(audio_path), acodec="libmp3lame", q=0)
        .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
    )


def _build_transcript_markdown(parsed: ParsedMedia, transcript_text: str, config: TranscriptionConfig) -> str:
    lines = [
        f"# {parsed.title or '未命名视频'}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 平台 | {parsed.platform} |",
        f"| 视频ID | `{parsed.video_id or ''}` |",
        f"| 原始链接 | {parsed.source_url} |",
        f"| 解析时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| 转写模型 | `{config.model}` |",
        "",
        "## 文案",
        "",
        transcript_text.strip(),
        "",
    ]
    return "\n".join(lines)
