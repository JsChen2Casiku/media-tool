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
    api_base: Optional[str] = Field(default=None, description="OpenAI 兼容接口基础地址或完整 /audio/transcriptions 地址")
    api_key: Optional[str] = Field(default=None, description="接口密钥")
    model: Optional[str] = Field(default=None, description="模型名称")


class ExtractRequest(DownloadRequest, AIConfigMixin):
    save_transcript: bool = Field(default=True, description="是否保存 transcript.md")
