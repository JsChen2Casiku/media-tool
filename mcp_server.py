from mcp.server.fastmcp import FastMCP

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
    api_base: str = "",
    api_key: str = "",
    model: str = "",
    output_dir: str = "",
    save_transcript: bool = True,
    save_video: bool = False,
    save_cover: bool = False,
    save_images: bool = False,
) -> dict:
    payload = ExtractRequest(
        text=text,
        output_dir=output_dir or None,
        api_base=api_base or None,
        api_key=api_key or None,
        model=model or None,
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
