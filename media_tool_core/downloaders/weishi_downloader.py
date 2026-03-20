import json
import random
import re

from media_tool_core.configs.general_constants import USER_AGENT_PC
from media_tool_core.configs.logging_config import logger
from media_tool_core.downloaders.base_downloader import BaseDownloader


class WeishiDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "content-type": "application/json; charset=UTF-8",
            "User-Agent": random.choice(USER_AGENT_PC),
            "referer": "https://isee.weishi.qq.com",
        }
        self.data = self.fetch_html_data()

    def fetch_html_data(self):
        self.html_content = self.fetch_html_content()
        pattern = re.compile(r"window\.Vise\.initState\s*=\s*(\{.*\};)", re.DOTALL)
        return BaseDownloader.parse_html_data(self.html_content, pattern)

    def get_real_video_url(self):
        try:
            data_dict = json.loads(self.data)
            video_url = data_dict["feedsList"][0]["videoUrl"]
            return video_url.replace("\\u002F", "/")
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse video URL: {e}")
            return None

    def get_title_content(self):
        try:
            data_dict = json.loads(self.data)
            return data_dict["feedsList"][0]["feedDesc"]
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse title content: {e}")
            return None

    def get_cover_photo_url(self):
        try:
            data_dict = json.loads(self.data)
            cover_url = data_dict["feedsList"][0]["videoCover"]
            return cover_url.replace("\\u002F", "/")
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse cover URL: {e}")
            return None

    def get_author_info(self):
        try:
            data_dict = json.loads(self.data)
            poster = data_dict["feedsList"][0].get("poster", {})
            return {
                "nickname": poster.get("nick", "未知用户"),
                "avatar": str(poster.get("avatar", "")).replace("\\u002F", "/"),
                "author_id": poster.get("id", ""),
            }
        except (KeyError, json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse author info: {e}")
            return None
