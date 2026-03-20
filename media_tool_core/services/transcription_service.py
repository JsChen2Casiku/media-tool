import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    segments: list[dict[str, Any]]


@dataclass(frozen=True)
class TranscriptionConfig:
    base_url: str
    task: str
    language: str | None
    timeout: int
    encode: bool
    word_timestamps: bool
    vad_filter: bool

    @classmethod
    def from_values(
        cls,
        transcription_base_url: str | None = None,
        transcription_task: str | None = None,
        transcription_language: str | None = None,
        transcription_timeout: int | None = None,
        transcription_encode: bool | None = None,
        transcription_word_timestamps: bool | None = None,
        transcription_vad_filter: bool | None = None,
    ) -> "TranscriptionConfig":
        base_url = (transcription_base_url or os.getenv("MEDIA_TOOL_TRANSCRIPTION_BASE_URL") or "").strip()
        if not base_url:
            raise ValueError(
                "未配置 Whisper ASR 服务地址。请设置 MEDIA_TOOL_TRANSCRIPTION_BASE_URL，"
                "或在请求中传入 transcription_base_url。"
            )

        task = (transcription_task or os.getenv("MEDIA_TOOL_TRANSCRIPTION_TASK") or "transcribe").strip().lower()
        if task not in {"transcribe", "translate"}:
            raise ValueError("transcription_task 只支持 transcribe 或 translate。")

        language = (transcription_language or os.getenv("MEDIA_TOOL_TRANSCRIPTION_LANGUAGE") or "").strip() or None
        timeout = transcription_timeout or int(os.getenv("MEDIA_TOOL_TRANSCRIPTION_TIMEOUT", "300"))
        encode = (
            transcription_encode
            if transcription_encode is not None
            else _read_bool_env("MEDIA_TOOL_TRANSCRIPTION_ENCODE", True)
        )
        word_timestamps = (
            transcription_word_timestamps
            if transcription_word_timestamps is not None
            else _read_bool_env("MEDIA_TOOL_TRANSCRIPTION_WORD_TIMESTAMPS", False)
        )
        vad_filter = (
            transcription_vad_filter
            if transcription_vad_filter is not None
            else _read_bool_env("MEDIA_TOOL_TRANSCRIPTION_VAD_FILTER", False)
        )

        return cls(
            base_url=base_url.rstrip("/"),
            task=task,
            language=language,
            timeout=timeout,
            encode=encode,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
        )

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/asr"

    @property
    def request_params(self) -> dict[str, str]:
        params = {
            "task": self.task,
            "output": "json",
            "encode": str(self.encode).lower(),
            "word_timestamps": str(self.word_timestamps).lower(),
            "vad_filter": str(self.vad_filter).lower(),
        }
        if self.language:
            params["language"] = self.language
        return params


class WhisperAsrTranscriber:
    def __init__(self, config: TranscriptionConfig):
        self.config = config

    def transcribe(self, media_path: Path) -> TranscriptionResult:
        content_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
        with media_path.open("rb") as file_obj:
            response = requests.post(
                self.config.endpoint,
                params=self.config.request_params,
                files={"audio_file": (media_path.name, file_obj, content_type)},
                timeout=(15, self.config.timeout),
            )

        if response.status_code >= 400:
            detail = response.text.strip()
            if len(detail) > 300:
                detail = detail[:300] + "..."
            raise ValueError(f"Whisper ASR 转写失败，HTTP {response.status_code}: {detail or '空响应'}")

        try:
            payload = response.json()
        except ValueError as exc:
            detail = response.text.strip()
            if len(detail) > 300:
                detail = detail[:300] + "..."
            raise ValueError(f"Whisper ASR 返回了非 JSON 响应: {detail or '空响应'}") from exc

        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("Whisper ASR 返回成功，但 text 为空。")

        segments = payload.get("segments")
        if not isinstance(segments, list):
            segments = []

        language = payload.get("language")
        return TranscriptionResult(text=text, language=language, segments=segments)


def create_transcriber(config: TranscriptionConfig) -> WhisperAsrTranscriber:
    return WhisperAsrTranscriber(config)
