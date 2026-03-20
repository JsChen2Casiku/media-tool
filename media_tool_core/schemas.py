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
    transcription_base_url: Optional[str] = Field(
        default=None,
        description="Whisper ASR 服务基地址，例如 http://127.0.0.1:9000",
    )
    transcription_task: Optional[str] = Field(
        default=None,
        description="转写任务，支持 transcribe 或 translate",
    )
    transcription_language: Optional[str] = Field(
        default=None,
        description="语言代码，例如 zh、en；留空时由 ASR 服务自动检测",
    )
    transcription_timeout: Optional[int] = Field(
        default=None,
        description="转写请求超时时间，单位秒",
    )
    transcription_encode: Optional[bool] = Field(
        default=None,
        description="是否让 Whisper 服务先重编码音频",
    )
    transcription_word_timestamps: Optional[bool] = Field(
        default=None,
        description="是否返回逐词时间戳",
    )
    transcription_vad_filter: Optional[bool] = Field(
        default=None,
        description="是否启用 VAD 静音过滤",
    )


class ExtractRequest(DownloadRequest, TranscriptionConfigMixin):
    save_transcript: bool = Field(default=True, description="是否保存 transcript.md")
