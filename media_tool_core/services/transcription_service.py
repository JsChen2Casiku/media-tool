import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

DEFAULT_API_BASE = os.getenv("MEDIA_TOOL_API_BASE", "https://api.openai.com/v1")
DEFAULT_API_KEY = os.getenv("MEDIA_TOOL_API_KEY", "")
DEFAULT_MODEL = os.getenv("MEDIA_TOOL_MODEL", "gpt-4o-mini-transcribe")
DEFAULT_TIMEOUT = int(os.getenv("MEDIA_TOOL_TRANSCRIPTION_TIMEOUT", "300"))


@dataclass
class TranscriptionConfig:
    api_base: str
    api_key: str
    model: str
    timeout: int = DEFAULT_TIMEOUT

    @classmethod
    def from_values(
        cls,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "TranscriptionConfig":
        return cls(
            api_base=(api_base or DEFAULT_API_BASE).strip(),
            api_key=(api_key or DEFAULT_API_KEY).strip(),
            model=(model or DEFAULT_MODEL).strip(),
        )

    @property
    def endpoint(self) -> str:
        base = self.api_base.rstrip("/")
        if base.endswith("/audio/transcriptions"):
            return base
        return f"{base}/audio/transcriptions"


class OpenAICompatibleTranscriber:
    def __init__(self, config: TranscriptionConfig):
        if not config.api_key:
            raise ValueError("缺少 API Key，请通过参数或环境变量 MEDIA_TOOL_API_KEY 提供。")
        self.config = config

    def transcribe(self, audio_path: Path) -> str:
        mime_type, _ = mimetypes.guess_type(audio_path.name)
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        data = {"model": self.config.model}

        with open(audio_path, "rb") as file_obj:
            files = {
                "file": (
                    audio_path.name,
                    file_obj,
                    mime_type or "application/octet-stream",
                )
            }
            response = requests.post(
                self.config.endpoint,
                headers=headers,
                data=data,
                files=files,
                timeout=self.config.timeout,
            )

        if response.status_code >= 400:
            raise ValueError(f"转写失败，HTTP {response.status_code}: {response.text}")

        payload = response.json()
        text = payload.get("text")
        if not text:
            raise ValueError(f"转写接口未返回 text 字段: {payload}")
        return text
