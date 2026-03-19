from __future__ import annotations

import asyncio
import mimetypes
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

DEFAULT_TRANSCRIBER_BACKEND = os.getenv("MEDIA_TOOL_TRANSCRIBER_BACKEND", "openai")
DEFAULT_API_BASE = os.getenv("MEDIA_TOOL_API_BASE", "https://api.openai.com/v1")
DEFAULT_API_KEY = os.getenv("MEDIA_TOOL_API_KEY", "")
DEFAULT_MODEL = os.getenv("MEDIA_TOOL_MODEL", "gpt-4o-mini-transcribe")
DEFAULT_TIMEOUT = int(os.getenv("MEDIA_TOOL_TRANSCRIPTION_TIMEOUT", "300"))

DEFAULT_FUNASR_MODEL = os.getenv("MEDIA_TOOL_FUNASR_MODEL", "paraformer-zh")
DEFAULT_FUNASR_VAD_MODEL = os.getenv("MEDIA_TOOL_FUNASR_VAD_MODEL", "fsmn-vad")
DEFAULT_FUNASR_PUNC_MODEL = os.getenv("MEDIA_TOOL_FUNASR_PUNC_MODEL", "ct-punc")
DEFAULT_FUNASR_DEVICE = os.getenv("MEDIA_TOOL_FUNASR_DEVICE", "auto")

DEFAULT_DOUBAOIME_MODEL = os.getenv("MEDIA_TOOL_DOUBAOIME_MODEL", "doubaoime-asr")
DEFAULT_DOUBAOIME_CREDENTIAL_PATH = os.getenv(
    "MEDIA_TOOL_DOUBAOIME_CREDENTIAL_PATH",
    "",
)
DEFAULT_DOUBAOIME_DEVICE_ID = os.getenv("MEDIA_TOOL_DOUBAOIME_DEVICE_ID", "")
DEFAULT_DOUBAOIME_TOKEN = os.getenv("MEDIA_TOOL_DOUBAOIME_TOKEN", "")
DEFAULT_DOUBAOIME_ENABLE_PUNCTUATION = (
    os.getenv("MEDIA_TOOL_DOUBAOIME_ENABLE_PUNCTUATION", "true").strip().lower()
    not in {"0", "false", "no", "off"}
)

_FUNASR_MODEL_CACHE: dict[tuple[str, str, str, str], object] = {}
_FUNASR_MODEL_CACHE_LOCK = threading.Lock()


@dataclass
class TranscriptionConfig:
    backend: str
    api_base: str
    api_key: str
    model: str
    timeout: int = DEFAULT_TIMEOUT
    funasr_vad_model: str = DEFAULT_FUNASR_VAD_MODEL
    funasr_punc_model: str = DEFAULT_FUNASR_PUNC_MODEL
    funasr_device: str = DEFAULT_FUNASR_DEVICE
    doubaoime_credential_path: str = DEFAULT_DOUBAOIME_CREDENTIAL_PATH
    doubaoime_device_id: str = DEFAULT_DOUBAOIME_DEVICE_ID
    doubaoime_token: str = DEFAULT_DOUBAOIME_TOKEN
    doubaoime_enable_punctuation: bool = DEFAULT_DOUBAOIME_ENABLE_PUNCTUATION

    @classmethod
    def from_values(
        cls,
        backend: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        funasr_vad_model: Optional[str] = None,
        funasr_punc_model: Optional[str] = None,
        funasr_device: Optional[str] = None,
        doubaoime_credential_path: Optional[str] = None,
        doubaoime_device_id: Optional[str] = None,
        doubaoime_token: Optional[str] = None,
        doubaoime_enable_punctuation: Optional[bool] = None,
    ) -> "TranscriptionConfig":
        resolved_backend = (backend or DEFAULT_TRANSCRIBER_BACKEND).strip().lower() or "openai"
        resolved_model = (model or "").strip()
        if not resolved_model:
            if resolved_backend == "funasr":
                resolved_model = DEFAULT_FUNASR_MODEL
            elif resolved_backend == "doubaoime":
                resolved_model = DEFAULT_DOUBAOIME_MODEL
            else:
                resolved_model = DEFAULT_MODEL

        return cls(
            backend=resolved_backend,
            api_base=(api_base or DEFAULT_API_BASE).strip(),
            api_key=(api_key or DEFAULT_API_KEY).strip(),
            model=resolved_model,
            timeout=DEFAULT_TIMEOUT,
            funasr_vad_model=(funasr_vad_model or DEFAULT_FUNASR_VAD_MODEL).strip(),
            funasr_punc_model=(funasr_punc_model or DEFAULT_FUNASR_PUNC_MODEL).strip(),
            funasr_device=(funasr_device or DEFAULT_FUNASR_DEVICE).strip() or "auto",
            doubaoime_credential_path=(
                doubaoime_credential_path or DEFAULT_DOUBAOIME_CREDENTIAL_PATH
            ).strip(),
            doubaoime_device_id=(doubaoime_device_id or DEFAULT_DOUBAOIME_DEVICE_ID).strip(),
            doubaoime_token=(doubaoime_token or DEFAULT_DOUBAOIME_TOKEN).strip(),
            doubaoime_enable_punctuation=(
                DEFAULT_DOUBAOIME_ENABLE_PUNCTUATION
                if doubaoime_enable_punctuation is None
                else bool(doubaoime_enable_punctuation)
            ),
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

        with audio_path.open("rb") as file_obj:
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


class FunASRTranscriber:
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.model = self._get_or_create_model()

    def _get_or_create_model(self):
        cache_key = (
            self.config.model,
            self.config.funasr_vad_model,
            self.config.funasr_punc_model,
            self._resolve_device(),
        )
        with _FUNASR_MODEL_CACHE_LOCK:
            cached_model = _FUNASR_MODEL_CACHE.get(cache_key)
            if cached_model is not None:
                return cached_model

            model = self._build_model(cache_key[3])
            _FUNASR_MODEL_CACHE[cache_key] = model
            return model

    def _build_model(self, resolved_device: str):
        try:
            from funasr import AutoModel
        except ModuleNotFoundError as exc:
            raise ValueError(
                "当前环境未安装 FunASR 依赖，请安装 funasr、modelscope、torch、torchaudio，"
                "或切换回 openai / doubaoime 转写后端。"
            ) from exc

        kwargs = {
            "model": self.config.model,
            "device": resolved_device,
        }
        if self.config.funasr_vad_model:
            kwargs["vad_model"] = self.config.funasr_vad_model
            kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}
        if self.config.funasr_punc_model:
            kwargs["punc_model"] = self.config.funasr_punc_model
        return AutoModel(**kwargs)

    def _resolve_device(self) -> str:
        requested = self.config.funasr_device.lower()
        if requested and requested != "auto":
            return requested
        try:
            import torch
        except ModuleNotFoundError:
            return "cpu"
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def transcribe(self, audio_path: Path) -> str:
        result = self.model.generate(input=str(audio_path), cache={}, batch_size_s=300)
        if not result:
            raise ValueError("FunASR 未返回任何转写结果。")

        first = result[0] if isinstance(result, list) else result
        text = first.get("text") if isinstance(first, dict) else None
        if not text:
            raise ValueError(f"FunASR 未返回 text 字段: {result}")

        if "sensevoice" in self.config.model.lower():
            try:
                from funasr.utils.postprocess_utils import rich_transcription_postprocess

                text = rich_transcription_postprocess(text)
            except Exception:
                pass
        return text.strip()


class DoubaoIMETranscriber:
    def __init__(self, config: TranscriptionConfig):
        self.config = config

    def transcribe(self, audio_path: Path) -> str:
        try:
            from doubaoime_asr import ASRConfig, transcribe
        except ModuleNotFoundError as exc:
            raise ValueError(
                "当前环境未安装 doubaoime-asr 依赖，请重新安装 requirements.txt 或重建 Docker 镜像。"
            ) from exc

        asr_config = ASRConfig(
            credential_path=self.config.doubaoime_credential_path or None,
            device_id=self.config.doubaoime_device_id or None,
            token=self.config.doubaoime_token or None,
            sample_rate=16000,
            channels=1,
            enable_punctuation=self.config.doubaoime_enable_punctuation,
        )

        try:
            text = _run_coroutine(transcribe(str(audio_path), config=asr_config, realtime=False))
        except Exception as exc:
            raise ValueError(f"豆包输入法 ASR 转写失败: {exc}") from exc

        if not text:
            raise ValueError("豆包输入法 ASR 未返回任何转写结果。")
        return text.strip()


def _run_coroutine(coroutine):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    result: dict[str, object] = {}
    error: dict[str, BaseException] = {}

    def runner():
        try:
            result["value"] = asyncio.run(coroutine)
        except BaseException as exc:
            error["value"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def create_transcriber(config: TranscriptionConfig):
    if config.backend == "funasr":
        return FunASRTranscriber(config)
    if config.backend == "doubaoime":
        return DoubaoIMETranscriber(config)
    if config.backend == "openai":
        return OpenAICompatibleTranscriber(config)
    raise ValueError(f"不支持的转写后端: {config.backend}")
