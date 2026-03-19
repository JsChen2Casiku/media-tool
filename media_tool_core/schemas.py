from typing import Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    text: str = Field(..., description="短视频分享文案或链接")


class DownloadRequest(ParseRequest):
    output_dir: Optional[str] = Field(
        default=None,
        description="输出目录，默认保存到 storage/exports",
    )
    save_video: bool = Field(default=True, description="是否下载视频")
    save_cover: bool = Field(default=True, description="是否下载封面")
    save_images: bool = Field(default=True, description="是否下载图集")


class TranscriptionConfigMixin(BaseModel):
    model: Optional[str] = Field(
        default=None,
        description=(
            "OpenTypeless 模型 ID，支持 "
            "doubao-asr、doubao-asr-official、"
            "doubao-asr-official-standard、doubao-asr-official-flash"
        ),
    )
    opentypeless_credential_path: Optional[str] = Field(
        default=None,
        description="IME 模式凭据缓存文件路径",
    )
    opentypeless_device_id: Optional[str] = Field(
        default=None,
        description="IME 模式设备 ID，可选",
    )
    opentypeless_token: Optional[str] = Field(
        default=None,
        description="IME 模式 Token，可选",
    )
    opentypeless_default_backend: Optional[str] = Field(
        default=None,
        description="默认后端，支持 ime 或 official",
    )
    opentypeless_official_mode: Optional[str] = Field(
        default=None,
        description="官方模式，支持 standard 或 flash",
    )
    opentypeless_official_app_key: Optional[str] = Field(
        default=None,
        description="官方文件识别 App Key",
    )
    opentypeless_official_access_key: Optional[str] = Field(
        default=None,
        description="官方文件识别 Access Key",
    )
    opentypeless_official_uid: Optional[str] = Field(
        default=None,
        description="官方文件识别请求 UID，可选",
    )


class ExtractRequest(DownloadRequest, TranscriptionConfigMixin):
    save_transcript: bool = Field(default=True, description="是否保存 transcript.md")
