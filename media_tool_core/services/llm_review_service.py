import os
from dataclasses import dataclass
from typing import Any

import requests


def _truncate_text(value: str, limit: int = 400) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


@dataclass(frozen=True)
class LlmReviewConfig:
    api_base: str
    api_key: str
    model: str
    timeout: int

    @classmethod
    def from_values(
        cls,
        llm_api_base: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_timeout: int | None = None,
    ) -> "LlmReviewConfig":
        return cls(
            api_base=(llm_api_base or os.getenv("MEDIA_TOOL_LLM_API_BASE") or "https://api.openai.com/v1").strip(),
            api_key=(llm_api_key or os.getenv("MEDIA_TOOL_LLM_API_KEY") or "").strip(),
            model=(llm_model or os.getenv("MEDIA_TOOL_LLM_MODEL") or "gpt-5.4").strip(),
            timeout=int(llm_timeout or os.getenv("MEDIA_TOOL_LLM_TIMEOUT") or "90"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def endpoint(self) -> str:
        normalized = self.api_base.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"


@dataclass(frozen=True)
class LlmReviewResult:
    text: str
    status: str
    applied: bool
    error: str | None = None


class OpenAiCompatibleReviewer:
    def __init__(self, config: LlmReviewConfig):
        self.config = config

    def review(self, transcript_text: str, title: str | None = None, platform: str | None = None) -> LlmReviewResult:
        if not self.config.is_configured:
            return LlmReviewResult(
                text=transcript_text,
                status="skipped",
                applied=False,
                error="未配置 LLM API Key，已跳过文案校正。",
            )

        response = requests.post(
            self.config.endpoint,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是专业中文短视频文案校对助手。"
                            "请仅对 ASR 转写文本做轻量校正：修正常见错别字、同音字误识别、断句、标点和明显语义不连贯处。"
                            "禁止编造事实，禁止总结改写，禁止扩写，禁止删除关键信息。"
                            "如果无法确定，就保留原文。"
                            "只输出最终校正后的正文，不要输出解释、标题、备注或 Markdown。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"平台：{platform or '未知'}\n"
                            f"标题：{title or '未知'}\n"
                            "请校正下面这段转写文案，保留原意和口语风格：\n\n"
                            f"{transcript_text}"
                        ),
                    },
                ],
            },
            timeout=(15, self.config.timeout),
        )

        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            raise ValueError(f"LLM 文案校正失败，HTTP {response.status_code}: {detail}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(f"LLM 文案校正返回了非 JSON 响应：{_truncate_text(response.text)}") from exc

        content = _extract_message_content(payload)
        if not content:
            raise ValueError("LLM 文案校正成功，但未返回有效文本。")

        return LlmReviewResult(text=content.strip(), status="applied", applied=True, error=None)


def create_reviewer(config: LlmReviewConfig) -> OpenAiCompatibleReviewer:
    return OpenAiCompatibleReviewer(config)


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            nested_text = item.get("content")
            if isinstance(nested_text, str) and nested_text.strip():
                parts.append(nested_text)
        return "\n".join(part.strip() for part in parts if part.strip())

    return ""


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return _truncate_text(response.text)

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return _truncate_text(message)
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return _truncate_text(message)
    return _truncate_text(response.text)
