import os
import shutil
from pathlib import Path


FFMPEG_ENV_VAR = "MEDIA_TOOL_FFMPEG_PATH"


def resolve_ffmpeg_binary() -> str | None:
    configured = (os.getenv(FFMPEG_ENV_VAR) or "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return str(candidate)

    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered

    for candidate in _iter_windows_ffmpeg_candidates():
        if candidate.is_file():
            return str(candidate)

    return None


def require_ffmpeg_binary() -> str:
    binary = resolve_ffmpeg_binary()
    if binary:
        return binary
    raise ValueError(
        "未检测到 ffmpeg 可执行文件。请将 ffmpeg 加入 PATH，或在环境变量 "
        "MEDIA_TOOL_FFMPEG_PATH 中显式指定 ffmpeg.exe 的完整路径。"
    )


def _iter_windows_ffmpeg_candidates() -> list[Path]:
    if os.name != "nt":
        return []

    home = Path.home()
    local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    user_profile = Path(os.getenv("USERPROFILE", ""))
    candidates = [
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"),
        home / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
        user_profile / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
        local_app_data / "Microsoft" / "WinGet" / "Packages",
    ]

    resolved: list[Path] = []
    for candidate in candidates:
        if candidate.name.lower() == "packages":
            resolved.extend(candidate.glob("Gyan.FFmpeg*\\ffmpeg-*\\bin\\ffmpeg.exe"))
        else:
            resolved.append(candidate)
    return resolved
