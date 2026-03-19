import json
import random
import re
from urllib.parse import unquote

from media_tool_core.configs.general_constants import USER_AGENT_M
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloaders.base_downloader import BaseDownloader

logger = get_logger(__name__)


class HaokanDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "content-type": "application/json; charset=UTF-8",
            "User-Agent": random.choice(USER_AGENT_M),
            "referer": "https://haokan.baidu.com/v",
        }
        self.data = self.fetch_html_data()

    def fetch_html_data(self):
        self.html_content = self.fetch_html_content()
        pattern = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*\};)", re.DOTALL)
        return BaseDownloader.parse_html_data(self.html_content, pattern)

    def get_real_video_url(self):
        try:
            data_dict = json.loads(self.data)
            clarity_url = data_dict.get("curVideoMeta", {}).get("clarityUrl", [])
            if clarity_url:
                video_url = clarity_url[-1].get("url", "")
                return unquote(video_url).replace("\\/", "/")
            return None
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse Haokan video URL: %s", exc)
            return None

    def get_title_content(self):
        try:
            data_dict = json.loads(self.data)
            return data_dict.get("curVideoMeta", {}).get("title", "")
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse Haokan title: %s", exc)
            return ""

    def get_cover_photo_url(self):
        try:
            data_dict = json.loads(self.data)
            cover_url = data_dict.get("curVideoMeta", {}).get("poster", "")
            return cover_url.replace("\\/", "/") if cover_url else ""
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse Haokan cover URL: %s", exc)
            return ""

    def get_author_info(self):
        try:
            data_dict = json.loads(self.data)
            author_node = data_dict.get("curVideoMeta", {}).get("mth", {})
            return {
                "nickname": author_node.get("author_name", ""),
                "author_id": str(author_node.get("mthid", "")),
                "avatar": author_node.get("author_photo", "").replace("\\/", "/"),
            }
        except (KeyError, json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Failed to parse Haokan author info: %s", exc)
            return {}
