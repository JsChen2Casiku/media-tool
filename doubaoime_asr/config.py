import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from .constants import AID, USER_AGENT, WEBSOCKET_URL
from .device import DeviceCredentials, get_asr_token, register_device


class _AudioInfo(BaseModel):
    channel: int
    format: str
    sample_rate: int


class _SessionExtraConfig(BaseModel):
    app_name: str
    cell_compress_rate: int
    did: str
    enable_asr_threepass: bool
    enable_asr_twopass: bool
    input_mode: str


class SessionConfig(BaseModel):
    audio_info: _AudioInfo
    enable_punctuation: bool
    enable_speech_rejection: bool
    extra: _SessionExtraConfig


@dataclass
class ASRConfig:
    url: str = WEBSOCKET_URL
    aid: str = AID
    user_agent: str = USER_AGENT
    device_id: Optional[str] = None
    token: Optional[str] = None
    credential_path: str | Path | None = None
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 20
    enable_punctuation: bool = True
    enable_speech_rejection: bool = False
    enable_asr_twopass: bool = True
    enable_asr_threepass: bool = True
    app_name: str = "com.android.chrome"
    connect_timeout: float = 10.0
    recv_timeout: float = 10.0
    _credentials: Optional[DeviceCredentials] = field(default=None, repr=False)
    _initialized: bool = field(default=False, repr=False)

    def _load_credentials_from_file(self) -> Optional[DeviceCredentials]:
        if self.credential_path is None:
            return None
        path = Path(self.credential_path).expanduser()
        if not path.exists():
            return None
        try:
            return DeviceCredentials(**json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_credentials_to_file(self, creds: DeviceCredentials):
        if self.credential_path is None:
            return
        path = Path(self.credential_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(creds.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def ensure_credentials(self):
        if self._initialized:
            return

        user_device_id = self.device_id
        user_token = self.token

        file_creds = self._load_credentials_from_file()
        if file_creds:
            self._credentials = file_creds
            if self.device_id is None:
                self.device_id = file_creds.device_id
            if self.token is None:
                self.token = file_creds.token

        need_save = False
        if self.device_id is None:
            self._credentials = register_device()
            self.device_id = self._credentials.device_id
            need_save = True

        if self.token is None:
            cdid = self._credentials.cdid if self._credentials else None
            self.token = get_asr_token(self.device_id, cdid)

        if self.credential_path and need_save and self._credentials:
            self._credentials.token = self.token
            self._save_credentials_to_file(self._credentials)

        if user_device_id is not None:
            self.device_id = user_device_id
        if user_token is not None:
            self.token = user_token

        self._initialized = True

    @property
    def ws_url(self) -> str:
        self.ensure_credentials()
        return f"{self.url}?aid={self.aid}&device_id={self.device_id}"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "proto-version": "v2",
            "x-custom-keepalive": "true",
        }

    def session_config(self) -> SessionConfig:
        self.ensure_credentials()
        audio_info = _AudioInfo(
            channel=self.channels,
            format="speech_opus",
            sample_rate=self.sample_rate,
        )
        extra = _SessionExtraConfig(
            app_name=self.app_name,
            cell_compress_rate=8,
            did=self.device_id,
            enable_asr_threepass=self.enable_asr_threepass,
            enable_asr_twopass=self.enable_asr_twopass,
            input_mode="tool",
        )
        return SessionConfig(
            audio_info=audio_info,
            enable_punctuation=self.enable_punctuation,
            enable_speech_rejection=self.enable_speech_rejection,
            extra=extra,
        )

    def get_token(self) -> str:
        self.ensure_credentials()
        return self.token
