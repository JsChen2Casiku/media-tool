from typing import Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    text: str = Field(..., description="短视频分享文案或链接")


class LoginRequest(BaseModel):
    username: str = Field(..., description="登录账号")
    password: str = Field(..., description="登录密码")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码，至少 6 位")
    confirm_password: str = Field(..., min_length=6, description="确认新密码")


class DownloadRequest(ParseRequest):
    output_dir: Optional[str] = Field(
        default=None,
        description="输出目录，默认保存到 runtime/storage/exports",
    )
    save_video: bool = Field(default=True, description="是否下载视频")
    save_cover: bool = Field(default=True, description="是否下载封面")
    save_images: bool = Field(default=True, description="是否下载图集")


class TranscriptionConfigMixin(BaseModel):
    transcription_base_url: Optional[str] = Field(
        default=None,
        description="Whisper ASR 服务基础地址，例如 http://127.0.0.1:9000",
    )
    transcription_task: Optional[str] = Field(
        default=None,
        description="转写任务，仅支持 transcribe 或 translate",
    )
    transcription_language: Optional[str] = Field(
        default=None,
        description="语言代码，例如 zh、en；留空时由 ASR 自动检测",
    )
    transcription_timeout: Optional[int] = Field(
        default=None,
        description="转写请求超时时间，单位秒",
    )
    transcription_encode: Optional[bool] = Field(
        default=None,
        description="是否先由 Whisper 服务进行重编码",
    )
    transcription_word_timestamps: Optional[bool] = Field(
        default=None,
        description="是否返回逐词时间戳",
    )
    transcription_vad_filter: Optional[bool] = Field(
        default=None,
        description="是否启用静音过滤",
    )


class LlmReviewConfigMixin(BaseModel):
    llm_api_base: Optional[str] = Field(
        default=None,
        description="OpenAI 兼容 LLM 基础地址，例如 https://api.openai.com/v1",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI 兼容 LLM 的 API Key；留空时跳过文案校正",
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="用于文案校正的模型名称，默认 gpt-5.4",
    )
    llm_timeout: Optional[int] = Field(
        default=None,
        description="LLM 文案校正超时时间，单位秒",
    )


class ExtractRequest(DownloadRequest, TranscriptionConfigMixin, LlmReviewConfigMixin):
    save_transcript: bool = Field(default=True, description="是否保存 transcript.md")
