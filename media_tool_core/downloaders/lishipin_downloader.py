import random
import re

from bs4 import BeautifulSoup

from media_tool_core.configs.general_constants import USER_AGENT_PC
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloaders.base_downloader import BaseDownloader
from media_tool_core.utils.web_fetcher import UrlParser

logger = get_logger(__name__)


class LishipinDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "content-type": "application/json; charset=UTF-8",
            "User-Agent": random.choice(USER_AGENT_PC),
            "referer": self.real_url,
        }
        self.video_id = UrlParser.get_video_id(self.real_url)
        self.data = self.fetch_html_data()
        self.html_content = self.fetch_html_content() or ""

    def fetch_html_data(self):
        api_url = "https://www.pearvideo.com/videoStatus.jsp"
        params = {
            "contId": "".join(filter(str.isdigit, self.video_id or "")),
            "mrd": random.random(),
        }
        try:
            response = self.session.get(api_url, params=params, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("PearVideo API request failed: %s", exc)
            return None

    def get_real_video_url(self):
        try:
            if not self.data:
                return None
            video_url = self.data.get("videoInfo", {}).get("videos", {}).get("srcUrl")
            if not video_url:
                return None
            new_value = f"cont-{self.video_id}"
            pattern = r"(\d+)-(\d+-hd\.mp4)"
            return re.sub(pattern, new_value + r"-\2", video_url)
        except Exception as exc:
            logger.warning("Failed to parse PearVideo video URL: %s", exc)
            return None

    def get_title_content(self):
        try:
            soup = BeautifulSoup(self.html_content, "html.parser")
            summary_div = soup.find("div", class_="summary")
            return summary_div.get_text(strip=True) if summary_div else ""
        except Exception as exc:
            logger.warning("Failed to parse PearVideo title: %s", exc)
            return ""

    def get_cover_photo_url(self):
        try:
            if not self.data:
                return ""
            return self.data.get("videoInfo", {}).get("video_image", "")
        except Exception as exc:
            logger.warning("Failed to parse PearVideo cover URL: %s", exc)
            return ""

    def get_author_info(self):
        try:
            soup = BeautifulSoup(self.html_content, "html.parser")
            author_node = soup.find("div", class_="thiscat")
            if not author_node:
                return {}

            name_node = author_node.find("div", class_="col-name")
            nickname = name_node.get_text(strip=True) if name_node else ""

            avatar_node = author_node.find("img")
            avatar = avatar_node["src"] if avatar_node and "src" in avatar_node.attrs else ""

            unique_id = ""
            subscribe_node = author_node.find("div", class_="column-subscribe")
            if subscribe_node and "data-userid" in subscribe_node.attrs:
                unique_id = subscribe_node["data-userid"]
            else:
                a_node = author_node.find("a", href=re.compile(r"author_(\d+)"))
                if a_node:
                    match = re.search(r"author_(\d+)", a_node["href"])
                    if match:
                        unique_id = match.group(1)

            return {
                "nickname": nickname,
                "author_id": unique_id,
                "avatar": avatar,
            }
        except Exception as exc:
            logger.warning("Failed to parse PearVideo author info: %s", exc)
            return {}
