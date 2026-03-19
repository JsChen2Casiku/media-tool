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
    model: str = "",
    credential_path: str = "",
    device_id: str = "",
    token: str = "",
    default_backend: str = "",
    official_mode: str = "",
    official_app_key: str = "",
    official_access_key: str = "",
    official_uid: str = "",
    output_dir: str = "",
    save_transcript: bool = True,
    save_video: bool = False,
    save_cover: bool = False,
    save_images: bool = False,
) -> dict:
    payload = ExtractRequest(
        text=text,
        output_dir=output_dir or None,
        model=model or None,
        opentypeless_credential_path=credential_path or None,
        opentypeless_device_id=device_id or None,
        opentypeless_token=token or None,
        opentypeless_default_backend=default_backend or None,
        opentypeless_official_mode=official_mode or None,
        opentypeless_official_app_key=official_app_key or None,
        opentypeless_official_access_key=official_access_key or None,
        opentypeless_official_uid=official_uid or None,
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
