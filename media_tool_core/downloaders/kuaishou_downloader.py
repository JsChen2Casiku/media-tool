import json
import random

from media_tool_core.configs.general_constants import USER_AGENT_PC
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloaders.base_downloader import BaseDownloader
from media_tool_core.utils.web_fetcher import UrlParser

logger = get_logger(__name__)


class KuaishouDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "content-type": "application/json; charset=UTF-8",
            "User-Agent": random.choice(USER_AGENT_PC),
            "referer": "https://www.kuaishou.com/",
        }
        self.video_id = UrlParser.get_video_id(self.real_url)
        self.html_content = self.fetch_html_content() or ""
        self.page_type, self.structured_data = self._identify_and_parse_data()
        self.client = self.structured_data.get("defaultClient", {}) if self.page_type == "VIDEO" else self.structured_data

    def _extract_json_object(self, text, start_index):
        if start_index == -1:
            return None
        bracket_count = 0
        found_start = False
        for index in range(start_index, len(text)):
            if text[index] == "{":
                bracket_count += 1
                found_start = True
            elif text[index] == "}":
                bracket_count -= 1
                if found_start and bracket_count == 0:
                    return text[start_index:index + 1]
        return None

    def _identify_and_parse_data(self):
        if "window.__APOLLO_STATE__" in self.html_content:
            marker = "window.__APOLLO_STATE__"
            start_pos = self.html_content.find(marker) + len(marker)
            start_pos = self.html_content.find("{", start_pos)
            json_str = self._extract_json_object(self.html_content, start_pos)
            if json_str:
                try:
                    return "VIDEO", json.loads(json_str)
                except json.JSONDecodeError as exc:
                    logger.warning("Failed to parse Kuaishou Apollo data: %s", exc)

        if "window.INIT_STATE" in self.html_content:
            marker = "window.INIT_STATE"
            start_pos = self.html_content.find(marker) + len(marker)
            start_pos = self.html_content.find("{", start_pos)
            json_str = self._extract_json_object(self.html_content, start_pos)
            if json_str:
                try:
                    return "ATLAS", json.loads(json_str, strict=False)
                except json.JSONDecodeError as exc:
                    logger.warning("Failed to parse Kuaishou INIT_STATE data: %s", exc)

        return "UNKNOWN", {}

    def get_real_video_url(self):
        if self.page_type != "VIDEO":
            return None
        try:
            video_url = self.client.get("VisionVideoSetRepresentation:1", {}).get("url")
            if not video_url:
                photo_key = f"VisionVideoDetailPhoto:{self.video_id}"
                video_url = self.client.get(photo_key, {}).get("photoUrl")
            return video_url.replace("\\u002F", "/") if video_url else None
        except Exception as exc:
            logger.warning("Failed to parse Kuaishou video URL: %s", exc)
            return None

    def get_title_content(self):
        try:
            photo_key = f"VisionVideoDetailPhoto:{self.video_id}"
            if self.page_type == "VIDEO":
                return self.client.get(photo_key, {}).get("caption", "")
            return ""
        except Exception as exc:
            logger.warning("Failed to parse Kuaishou title: %s", exc)
            return ""

    def get_cover_photo_url(self):
        try:
            photo_key = f"VisionVideoDetailPhoto:{self.video_id}"
            return self.client.get(photo_key, {}).get("coverUrl", "")
        except Exception as exc:
            logger.warning("Failed to parse Kuaishou cover URL: %s", exc)
            return ""

    def get_author_info(self):
        try:
            if self.page_type == "VIDEO":
                photo_key = f"VisionVideoDetailPhoto:{self.video_id}"
                author_ref = self.client.get(photo_key, {}).get("author")
                if not author_ref:
                    for key, value in self.client.items():
                        if f'photoId":"{self.video_id}"' in key and isinstance(value, dict):
                            author_ref = value.get("author")
                            break
                if author_ref and author_ref.get("id") in self.client:
                    author_detail = self.client[author_ref["id"]]
                    return {
                        "nickname": author_detail.get("name"),
                        "author_id": author_detail.get("id"),
                        "avatar": author_detail.get("headerUrl"),
                    }

            if self.page_type == "ATLAS":
                for value in self.structured_data.values():
                    if isinstance(value, dict) and "userProfile" in value:
                        profile = value["userProfile"].get("profile", {})
                        return {
                            "nickname": profile.get("user_name"),
                            "author_id": profile.get("user_id"),
                            "avatar": profile.get("headurl"),
                        }
        except Exception as exc:
            logger.warning("Failed to parse Kuaishou author info: %s", exc)
        return None
