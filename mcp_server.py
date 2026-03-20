from mcp.server.fastmcp import FastMCP

from media_tool_core.configs.env_loader import load_project_env

load_project_env()

from media_tool_core.schemas import DownloadRequest, ExtractRequest
from media_tool_core.services.media_service import download_media, extract_transcript, parse_media

mcp = FastMCP("media-tool")


@mcp.tool()
def parse_media_info(text: str) -> dict:
    return parse_media(text)


@mcp.tool()
def download_media_assets(
    text: str,
    output_dir: str = "",
    save_video: bool = True,
    save_cover: bool = True,
    save_images: bool = True,
) -> dict:
    payload = DownloadRequest(
        text=text,
        output_dir=output_dir or None,
        save_video=save_video,
        save_cover=save_cover,
        save_images=save_images,
    )
    return download_media(payload)


@mcp.tool()
def extract_media_copy(
    text: str,
    transcription_base_url: str = "",
    transcription_task: str = "",
    transcription_language: str = "",
    transcription_timeout: int = 0,
    transcription_encode: bool | None = None,
    transcription_word_timestamps: bool | None = None,
    transcription_vad_filter: bool | None = None,
    llm_api_base: str = "",
    llm_api_key: str = "",
    llm_model: str = "",
    llm_timeout: int = 0,
    output_dir: str = "",
    save_transcript: bool = True,
    save_video: bool = False,
    save_cover: bool = False,
    save_images: bool = False,
) -> dict:
    payload = ExtractRequest(
        text=text,
        output_dir=output_dir or None,
        transcription_base_url=transcription_base_url or None,
        transcription_task=transcription_task or None,
        transcription_language=transcription_language or None,
        transcription_timeout=transcription_timeout or None,
        transcription_encode=transcription_encode,
        transcription_word_timestamps=transcription_word_timestamps,
        transcription_vad_filter=transcription_vad_filter,
        llm_api_base=llm_api_base or None,
        llm_api_key=llm_api_key or None,
        llm_model=llm_model or None,
        llm_timeout=llm_timeout or None,
        save_transcript=save_transcript,
        save_video=save_video,
        save_cover=save_cover,
        save_images=save_images,
    )
    return extract_transcript(payload)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
