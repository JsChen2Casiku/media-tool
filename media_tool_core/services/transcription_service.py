from __future__ import annotations

import asyncio
import base64
import os
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import requests

IME_MODEL_ID = "doubao-asr"
OFFICIAL_MODEL_ID = "doubao-asr-official"
OFFICIAL_STANDARD_MODEL_ID = "doubao-asr-official-standard"
OFFICIAL_FLASH_MODEL_ID = "doubao-asr-official-flash"

DEFAULT_MODEL = os.getenv("MEDIA_TOOL_OPENTYPELESS_MODEL", IME_MODEL_ID)
DEFAULT_CREDENTIAL_PATH = os.getenv("MEDIA_TOOL_OPENTYPELESS_CREDENTIAL_PATH", "")
DEFAULT_DEVICE_ID = os.getenv("MEDIA_TOOL_OPENTYPELESS_DEVICE_ID", "")
DEFAULT_TOKEN = os.getenv("MEDIA_TOOL_OPENTYPELESS_TOKEN", "")
DEFAULT_DEFAULT_BACKEND = os.getenv("MEDIA_TOOL_OPENTYPELESS_DEFAULT_BACKEND", "ime")
DEFAULT_OFFICIAL_MODE = os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODE", "flash")
DEFAULT_OFFICIAL_APP_KEY = os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY", "")
DEFAULT_OFFICIAL_ACCESS_KEY = os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY", "")
DEFAULT_OFFICIAL_STANDARD_SUBMIT_ENDPOINT = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_SUBMIT_ENDPOINT",
    "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit",
)
DEFAULT_OFFICIAL_STANDARD_QUERY_ENDPOINT = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_QUERY_ENDPOINT",
    "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query",
)
DEFAULT_OFFICIAL_FLASH_ENDPOINT = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_ENDPOINT",
    "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
)
DEFAULT_OFFICIAL_STANDARD_RESOURCE_ID = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_RESOURCE_ID",
    "volc.seedasr.auc",
)
DEFAULT_OFFICIAL_FLASH_RESOURCE_ID = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_RESOURCE_ID",
    "volc.bigasr.auc_turbo",
)
DEFAULT_OFFICIAL_MODEL_NAME = os.getenv(
    "MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODEL_NAME",
    "bigmodel",
)
DEFAULT_OFFICIAL_UID = os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_UID", "opentypeless")
DEFAULT_OFFICIAL_TIMEOUT_SEC = int(
    os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_TIMEOUT_SEC", "120")
)
DEFAULT_OFFICIAL_QUERY_INTERVAL_SEC = float(
    os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_INTERVAL_SEC", "1.0")
)
DEFAULT_OFFICIAL_QUERY_TIMEOUT_SEC = int(
    os.getenv("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_TIMEOUT_SEC", "300")
)
DEFAULT_SAMPLE_RATE = int(os.getenv("MEDIA_TOOL_OPENTYPELESS_SAMPLE_RATE", "16000"))
DEFAULT_CHANNELS = int(os.getenv("MEDIA_TOOL_OPENTYPELESS_CHANNELS", "1"))
DEFAULT_FRAME_DURATION_MS = int(
    os.getenv("MEDIA_TOOL_OPENTYPELESS_FRAME_DURATION_MS", "20")
)


class BackendMode(str, Enum):
    IME = "ime"
    OFFICIAL = "official"


class OfficialMode(str, Enum):
    STANDARD = "standard"
    FLASH = "flash"


@dataclass
class TranscriptionConfig:
    model: str = DEFAULT_MODEL
    credential_path: str = DEFAULT_CREDENTIAL_PATH
    device_id: str = DEFAULT_DEVICE_ID
    token: str = DEFAULT_TOKEN
    default_backend: str = DEFAULT_DEFAULT_BACKEND
    official_mode: str = DEFAULT_OFFICIAL_MODE
    official_app_key: str = DEFAULT_OFFICIAL_APP_KEY
    official_access_key: str = DEFAULT_OFFICIAL_ACCESS_KEY
    official_standard_submit_endpoint: str = DEFAULT_OFFICIAL_STANDARD_SUBMIT_ENDPOINT
    official_standard_query_endpoint: str = DEFAULT_OFFICIAL_STANDARD_QUERY_ENDPOINT
    official_flash_endpoint: str = DEFAULT_OFFICIAL_FLASH_ENDPOINT
    official_standard_resource_id: str = DEFAULT_OFFICIAL_STANDARD_RESOURCE_ID
    official_flash_resource_id: str = DEFAULT_OFFICIAL_FLASH_RESOURCE_ID
    official_model_name: str = DEFAULT_OFFICIAL_MODEL_NAME
    official_uid: str = DEFAULT_OFFICIAL_UID
    official_timeout_sec: int = DEFAULT_OFFICIAL_TIMEOUT_SEC
    official_query_interval_sec: float = DEFAULT_OFFICIAL_QUERY_INTERVAL_SEC
    official_query_timeout_sec: int = DEFAULT_OFFICIAL_QUERY_TIMEOUT_SEC
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    frame_duration_ms: int = DEFAULT_FRAME_DURATION_MS

    @classmethod
    def from_values(
        cls,
        model: Optional[str] = None,
        opentypeless_credential_path: Optional[str] = None,
        opentypeless_device_id: Optional[str] = None,
        opentypeless_token: Optional[str] = None,
        opentypeless_default_backend: Optional[str] = None,
        opentypeless_official_mode: Optional[str] = None,
        opentypeless_official_app_key: Optional[str] = None,
        opentypeless_official_access_key: Optional[str] = None,
        opentypeless_official_uid: Optional[str] = None,
    ) -> "TranscriptionConfig":
        return cls(
            model=(model or DEFAULT_MODEL).strip() or IME_MODEL_ID,
            credential_path=(opentypeless_credential_path or DEFAULT_CREDENTIAL_PATH).strip(),
            device_id=(opentypeless_device_id or DEFAULT_DEVICE_ID).strip(),
            token=(opentypeless_token or DEFAULT_TOKEN).strip(),
            default_backend=(opentypeless_default_backend or DEFAULT_DEFAULT_BACKEND).strip()
            or BackendMode.IME.value,
            official_mode=(opentypeless_official_mode or DEFAULT_OFFICIAL_MODE).strip()
            or OfficialMode.FLASH.value,
            official_app_key=(
                opentypeless_official_app_key or DEFAULT_OFFICIAL_APP_KEY
            ).strip(),
            official_access_key=(
                opentypeless_official_access_key or DEFAULT_OFFICIAL_ACCESS_KEY
            ).strip(),
            official_uid=(opentypeless_official_uid or DEFAULT_OFFICIAL_UID).strip()
            or DEFAULT_OFFICIAL_UID,
        )

    @property
    def resolved_backend(self) -> BackendMode:
        normalized = self.model.strip().lower()
        if normalized in {
            OFFICIAL_MODEL_ID,
            OFFICIAL_STANDARD_MODEL_ID,
            OFFICIAL_FLASH_MODEL_ID,
            BackendMode.OFFICIAL.value,
        }:
            return BackendMode.OFFICIAL
        if normalized == IME_MODEL_ID:
            return BackendMode.IME
        try:
            return BackendMode(self.default_backend.lower())
        except ValueError:
            return BackendMode.IME

    @property
    def resolved_official_mode(self) -> OfficialMode:
        normalized = self.model.strip().lower()
        if normalized in {OFFICIAL_STANDARD_MODEL_ID, "official-standard", "standard"}:
            return OfficialMode.STANDARD
        if normalized in {OFFICIAL_FLASH_MODEL_ID, "official-flash", "flash"}:
            return OfficialMode.FLASH
        try:
            return OfficialMode(self.official_mode.lower())
        except ValueError:
            return OfficialMode.FLASH


class OpenTypelessTranscriber:
    def __init__(self, config: TranscriptionConfig):
        self.config = config

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise ValueError("转写音频为空，无法提交 OpenTypeless。")

        if self.config.resolved_backend == BackendMode.OFFICIAL:
            audio_bytes = audio_path.read_bytes()
            return asyncio.run(self._official_transcribe(audio_bytes))
        return asyncio.run(self._ime_transcribe(audio_path))

    async def _ime_transcribe(self, audio_path: Path) -> str:
        try:
            from doubaoime_asr import ASRConfig, ResponseType, transcribe_stream
        except ModuleNotFoundError as exc:
            raise ValueError(
                "当前环境缺少 OpenTypeless IME 模式依赖，请重新安装 requirements.txt 或重建 Docker 镜像。"
            ) from exc

        kwargs = {
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels,
            "frame_duration_ms": self.config.frame_duration_ms,
        }
        if self.config.credential_path:
            kwargs["credential_path"] = self.config.credential_path
        if self.config.device_id:
            kwargs["device_id"] = self.config.device_id
        if self.config.token:
            kwargs["token"] = self.config.token

        final_texts: list[str] = []
        async for response in transcribe_stream(
            str(audio_path),
            config=ASRConfig(**kwargs),
            realtime=False,
        ):
            if response.type == ResponseType.FINAL_RESULT:
                final_texts.append(response.text or "")
            elif response.type == ResponseType.ERROR:
                raise ValueError(f"OpenTypeless IME 转写失败: {response.error_msg}")

        return "".join(final_texts).strip()

    async def _official_transcribe(self, audio_data: bytes) -> str:
        mode = self.config.resolved_official_mode
        if mode == OfficialMode.STANDARD:
            return await asyncio.to_thread(self._official_standard_transcribe, audio_data)
        return await asyncio.to_thread(self._official_flash_transcribe, audio_data)

    def _resolve_official_credentials(self) -> tuple[str, str]:
        missing = []
        if not self.config.official_app_key:
            missing.append("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY")
        if not self.config.official_access_key:
            missing.append("MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY")
        if missing:
            raise ValueError(f"缺少官方文件识别配置: {', '.join(missing)}")
        return self.config.official_app_key, self.config.official_access_key

    def _build_request_headers(
        self,
        resource_id: str,
        request_id: str,
        app_key: str,
        access_key: str,
    ) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-App-Key": app_key,
            "X-Api-Access-Key": access_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
        }

    def _build_audio_payload(self, audio_data: bytes) -> dict[str, str]:
        return {"data": base64.b64encode(audio_data).decode("utf-8")}

    def _request_json(
        self,
        url: str,
        headers: dict[str, str],
        body: dict,
    ) -> tuple[dict, dict[str, str]]:
        try:
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=self.config.official_timeout_sec,
            )
        except requests.RequestException as exc:
            raise ValueError(f"OpenTypeless 官方请求失败: {exc}") from exc

        response_headers = {key.lower(): value for key, value in response.headers.items()}
        if response.status_code >= 400:
            raise ValueError(
                f"OpenTypeless 官方请求失败，HTTP {response.status_code}: {response.text[:500]}"
            )

        if not response.text:
            return {}, response_headers

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("OpenTypeless 官方接口返回了非 JSON 数据。") from exc
        return payload, response_headers

    def _status_code(self, payload: dict, headers: dict[str, str]) -> Optional[str]:
        value = headers.get("x-api-status-code")
        if value is not None:
            return str(value)
        code = payload.get("code")
        return None if code is None else str(code)

    def _status_message(self, payload: dict, headers: dict[str, str]) -> str:
        return str(
            payload.get("message")
            or payload.get("msg")
            or headers.get("x-api-message")
            or "unknown error"
        )

    def _extract_text(self, payload: dict) -> str:
        result = payload.get("result")
        if isinstance(result, dict):
            text = result.get("text")
            if isinstance(text, str):
                return text
        if isinstance(result, list):
            parts: list[str] = []
            for item in result:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "".join(parts)
        if isinstance(payload.get("text"), str):
            return payload["text"]
        return ""

    def _official_flash_transcribe(self, audio_data: bytes) -> str:
        app_key, access_key = self._resolve_official_credentials()
        request_id = str(uuid.uuid4())
        headers = self._build_request_headers(
            self.config.official_flash_resource_id,
            request_id,
            app_key,
            access_key,
        )
        body = {
            "user": {"uid": self.config.official_uid},
            "audio": self._build_audio_payload(audio_data),
            "request": {"model_name": self.config.official_model_name},
        }
        payload, response_headers = self._request_json(
            self.config.official_flash_endpoint,
            headers,
            body,
        )
        status = self._status_code(payload, response_headers)
        if status == "20000003":
            return ""
        if status and status != "20000000":
            raise ValueError(
                "OpenTypeless 官方极速版转写失败: "
                f"status={status}, message={self._status_message(payload, response_headers)}"
            )

        text = self._extract_text(payload)
        if not text:
            raise ValueError(f"OpenTypeless 官方极速版未返回文本: {payload}")
        return text.strip()

    def _official_standard_transcribe(self, audio_data: bytes) -> str:
        app_key, access_key = self._resolve_official_credentials()
        request_id = str(uuid.uuid4())
        submit_headers = self._build_request_headers(
            self.config.official_standard_resource_id,
            request_id,
            app_key,
            access_key,
        )
        submit_body = {
            "user": {"uid": self.config.official_uid},
            "audio": self._build_audio_payload(audio_data),
            "request": {"model_name": self.config.official_model_name},
        }
        submit_payload, submit_response_headers = self._request_json(
            self.config.official_standard_submit_endpoint,
            submit_headers,
            submit_body,
        )
        submit_status = self._status_code(submit_payload, submit_response_headers)
        if submit_status and submit_status != "20000000":
            raise ValueError(
                "OpenTypeless 官方标准版提交失败: "
                f"status={submit_status}, message={self._status_message(submit_payload, submit_response_headers)}"
            )

        task_id = submit_response_headers.get("x-api-request-id") or request_id
        query_headers = self._build_request_headers(
            self.config.official_standard_resource_id,
            task_id,
            app_key,
            access_key,
        )
        deadline = time.monotonic() + self.config.official_query_timeout_sec

        while True:
            if time.monotonic() >= deadline:
                raise ValueError("OpenTypeless 官方标准版查询超时。")

            query_payload, query_response_headers = self._request_json(
                self.config.official_standard_query_endpoint,
                query_headers,
                {},
            )
            query_status = self._status_code(query_payload, query_response_headers)
            if query_status == "20000000":
                text = self._extract_text(query_payload)
                if not text:
                    raise ValueError(f"OpenTypeless 官方标准版未返回文本: {query_payload}")
                return text.strip()

            if query_status == "20000003":
                return ""

            if query_status in {"20000001", "20000002"}:
                time.sleep(self.config.official_query_interval_sec)
                continue

            raise ValueError(
                "OpenTypeless 官方标准版查询失败: "
                f"status={query_status}, message={self._status_message(query_payload, query_response_headers)}"
            )


def create_transcriber(config: TranscriptionConfig) -> OpenTypelessTranscriber:
    return OpenTypelessTranscriber(config)
