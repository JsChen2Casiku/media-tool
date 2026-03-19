import random
import re
from urllib.parse import parse_qs, urlparse

import requests

from media_tool_core.configs.general_constants import DOMAIN_TO_PLATFORM, USER_AGENT_PC
from media_tool_core.configs.logging_config import logger


class WebFetcher:
    headers = {
        "content-type": "application/json; charset=UTF-8",
        "User-Agent": random.choice(USER_AGENT_PC),
    }

    @staticmethod
    def fetch_redirect_url(url, max_redirects=5):
        try:
            current_url = url
            redirect_url = None
            for _ in range(max_redirects):
                response = requests.get(current_url, headers=WebFetcher.headers, allow_redirects=False, timeout=5)
                response.raise_for_status()
                redirect_url = response.headers.get("location")
                if not redirect_url:
                    break
                if DOMAIN_TO_PLATFORM.get(UrlParser.get_domain(redirect_url)):
                    break
                current_url = redirect_url
            if redirect_url:
                return UrlParser.extract_video_address(redirect_url)
            if DOMAIN_TO_PLATFORM.get(UrlParser.get_domain(url)):
                return UrlParser.extract_video_address(url)
            return None
        except requests.RequestException as exc:
            logger.error("Failed to get the page: %s", exc)
            return None
        except Exception as exc:
            logger.error("An error occurred: %s", exc)
            return None


class UrlParser:
    @staticmethod
    def convert_to_https(url):
        if not url:
            return None
        if url.startswith("http://"):
            return "https://" + url[7:]
        return url

    @staticmethod
    def get_url(text):
        url_pattern = re.compile(r"\bhttps?:\/\/(?:www\.|[-a-zA-Z0-9.@:%_+~#=]{1,256}\.[a-zA-Z0-9()]{1,6})\b(?:[-a-zA-Z0-9()@:%_+.~#?&//=]*)?")
        match = url_pattern.search(text)
        return match.group() if match else None

    @staticmethod
    def get_domain(url):
        return urlparse(url).netloc

    @staticmethod
    def extract_video_address(url):
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        platform = DOMAIN_TO_PLATFORM.get(domain)
        address = f"{parsed_url.scheme}://{domain}{parsed_url.path}".rstrip("/")
        query_params = parse_qs(parsed_url.query)

        if platform == "haokan":
            vid = query_params.get("vid", [None])[0]
            if vid:
                address = f"{address}?vid={vid}"
        elif platform == "weishi":
            video_id = query_params.get("id", [None])[0]
            if video_id:
                address = f"{address}?id={video_id}"
        elif platform == "xiaohongshu":
            xsec_token = query_params.get("xsec_token", [None])[0]
            if xsec_token:
                address = f"{address}?xsec_token={xsec_token}"
        elif platform == "kuaishou":
            address = address.replace("http://", "https://")
        elif platform == "douyin":
            modal_id = query_params.get("modal_id", [None])[0]
            if modal_id:
                address = f"{address}?modal_id={modal_id}"
        elif platform == "youtube":
            video_id = query_params.get("v", [None])[0]
            if video_id:
                address = f"{address}?v={video_id}"
        return address

    @staticmethod
    def get_video_id(url):
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            for key in ["vid", "id", "modal_id", "v"]:
                value = query_params.get(key, [None])[0]
                if value:
                    return value
            path_segments = parsed_url.path.strip("/").split("/")
            return path_segments[-1] if path_segments else None
        except Exception as exc:
            logger.error("An error occurred while extracting video ID: %s", exc)
            return None

    @staticmethod
    def generate_video_url(platform, video_id):
        url_map = {
            "pipigaoxiao": "https://h5.pipigx.com/pp/post/",
            "haokan": "https://haokan.hao123.com/v?vid=",
            "bilibili": "https://www.bilibili.com/video/",
            "douyin": "https://www.iesdouyin.com/share/video/",
            "kuaishou": "https://www.kuaishou.com/short-video/",
            "pearvideo": "https://www.pearvideo.com/",
            "acfun": "https://www.acfun.cn/v/",
            "instagram": "https://www.instagram.com/p/",
            "tiktok": "https://www.tiktok.com/@/video/",
            "twitter": "https://twitter.com/x/status/",
            "weibo": "https://m.weibo.cn/status/",
            "ixigua": "https://www.ixigua.com/",
            "youtube": "https://www.youtube.com/watch?v=",
            "zhihu": "https://www.zhihu.com/question/",
        }
        if platform not in url_map:
            return "Error: 不支持的平台"
        return url_map[platform] + video_id
