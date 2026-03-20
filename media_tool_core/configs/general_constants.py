import os
from pathlib import Path
from typing import Final

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
RUNTIME_ROOT = os.getenv("MEDIA_TOOL_RUNTIME_ROOT", os.path.join(PROJECT_ROOT, "runtime"))
DOMAIN = os.getenv("DOMAIN", "")

STORAGE_ROOT = os.getenv("MEDIA_TOOL_STORAGE_ROOT", os.path.join(RUNTIME_ROOT, "storage"))
LOG_ROOT = os.getenv("MEDIA_TOOL_LOG_ROOT", os.path.join(RUNTIME_ROOT, "logs"))
SAVE_VIDEO_PATH = os.path.join(STORAGE_ROOT, "videos")
SAVE_IMAGE_PATH = os.path.join(STORAGE_ROOT, "images")
SAVE_COVER_PATH = os.path.join(STORAGE_ROOT, "covers")
SAVE_TEXT_PATH = os.path.join(STORAGE_ROOT, "transcripts")
TEMP_PATH = os.path.join(STORAGE_ROOT, "temp")
LOG_PATH = LOG_ROOT

MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_SIZE_MB", "15"))
MAX_CACHE_SIZE_BYTES = MAX_CACHE_SIZE_MB * 1024 * 1024
REQUEST_TIMEOUT = int(os.getenv("MEDIA_TOOL_REQUEST_TIMEOUT", "30"))

PLATFORM_LABELS: Final[dict[str, str]] = {
    "xiaohongshu": "小红书",
    "douyin": "抖音",
    "kuaishou": "快手",
    "bilibili": "哔哩哔哩",
    "haokan": "好看视频",
    "weishi": "微视",
    "pearvideo": "梨视频",
    "pipigaoxiao": "皮皮搞笑",
    "acfun": "AcFun",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "twitter": "Twitter",
    "weibo": "微博",
    "ixigua": "西瓜视频",
    "youtube": "YouTube",
    "zhihu": "知乎",
}

DOMAIN_TO_PLATFORM: Final[dict[str, str]] = {
    "www.xiaohongshu.com": "xiaohongshu",
    "www.douyin.com": "douyin",
    "www.iesdouyin.com": "douyin",
    "www.kuaishou.com": "kuaishou",
    "www.bilibili.com": "bilibili",
    "haokan.baidu.com": "haokan",
    "haokan.hao123.com": "haokan",
    "isee.weishi.qq.com": "weishi",
    "video.weishi.qq.com": "weishi",
    "www.pearvideo.com": "pearvideo",
    "h5.pipigx.com": "pipigaoxiao",
    "m.acfun.cn": "acfun",
    "www.acfun.cn": "acfun",
    "www.instagram.com": "instagram",
    "instagram.com": "instagram",
    "www.tiktok.com": "tiktok",
    "vt.tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "weibo.com": "weibo",
    "m.weibo.cn": "weibo",
    "www.ixigua.com": "ixigua",
    "v.ixigua.com": "ixigua",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "m.youtube.com": "youtube",
    "www.zhihu.com": "zhihu",
    "zhuanlan.zhihu.com": "zhihu",
}

# 兼容旧命名，避免其他模块仍引用该常量时出错。
DOMAIN_TO_NAME = DOMAIN_TO_PLATFORM

USER_AGENT_PC = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

USER_AGENT_M = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S9180) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
]


def get_platform_label(platform_key: str) -> str:
    return PLATFORM_LABELS.get(platform_key, platform_key)


def check_essential_dirs() -> None:
    for dir_path in [SAVE_VIDEO_PATH, SAVE_IMAGE_PATH, SAVE_COVER_PATH, SAVE_TEXT_PATH, TEMP_PATH, LOG_PATH]:
        os.makedirs(dir_path, exist_ok=True)


check_essential_dirs()
