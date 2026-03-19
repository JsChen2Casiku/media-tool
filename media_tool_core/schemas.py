from typing import Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    text: str = Field(..., description="短视频分享文案或链接")


class DownloadRequest(ParseRequest):
    output_dir: Optional[str] = Field(default=None, description="输出目录，默认保存到 storage/exports")
    save_video: bool = Field(default=True, description="是否下载视频")
    save_cover: bool = Field(default=True, description="是否下载封面")
    save_images: bool = Field(default=True, description="是否下载图集")


class AIConfigMixin(BaseModel):
    backend: Optional[str] = Field(
        default=None,
        description="转写后端，支持 openai、funasr、doubaoime",
    )
    api_base: Optional[str] = Field(
        default=None,
        description="OpenAI 兼容接口基础地址，或完整的 /audio/transcriptions 地址",
    )
    api_key: Optional[str] = Field(default=None, description="接口密钥")
    model: Optional[str] = Field(
        default=None,
        description="模型名称。openai 后端表示转写模型，funasr 后端表示本地模型，doubaoime 后端仅用于结果标识。",
    )
    funasr_vad_model: Optional[str] = Field(default=None, description="FunASR VAD 模型名")
    funasr_punc_model: Optional[str] = Field(default=None, description="FunASR 标点模型名")
    funasr_device: Optional[str] = Field(
        default=None,
        description="FunASR 运行设备，例如 auto、cpu、cuda:0",
    )
    doubaoime_credential_path: Optional[str] = Field(
        default=None,
        description="doubaoime-asr 凭据缓存文件路径，首次运行可自动注册并写入",
    )
    doubaoime_device_id: Optional[str] = Field(
        default=None,
        description="doubaoime-asr 设备 ID，可选",
    )
    doubaoime_token: Optional[str] = Field(
        default=None,
        description="doubaoime-asr 认证 Token，可选",
    )
    doubaoime_enable_punctuation: Optional[bool] = Field(
        default=None,
        description="doubaoime-asr 是否启用标点",
    )


class ExtractRequest(DownloadRequest, AIConfigMixin):
    save_transcript: bool = Field(default=True, description="是否保存 transcript.md")
