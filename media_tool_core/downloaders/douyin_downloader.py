import copy
import json

import urllib3
import warnings

from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloaders.base_downloader import BaseDownloader
from media_tool_core.utils.douyin_utils.bogus_sign_utils import CommonUtils
from media_tool_core.utils.web_fetcher import UrlParser

logger = get_logger(__name__)

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


class DouyinDownloader(BaseDownloader):
    _TTWID_CACHE = None

    def __init__(self, real_url):
        super().__init__(real_url)
        self.common_utils = CommonUtils()
        self.headers = {
            "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "Accept": "application/json, text/plain, */*",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": self.common_utils.user_agent,
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.ms_token = self.common_utils.get_ms_token()
        self.ttwid = "1%7CvDWCB8tYdKPbdOlqwNTkDPhizBaV9i91KjYLKJbqurg%7C1723536402%7C314e63000decb79f46b8ff255560b29f4d8c57352dad465b41977db4830b4c7e"
        self.webid = "7307457174287205926"
        self.fetch_html_content()
        self.aweme_id = UrlParser.get_video_id(self.real_url)
        self.data = self.fetch_html_data()

    def _get_ttwid(self):
        """动态获取 ttwid，并使用类级缓存减少重复请求。"""
        if DouyinDownloader._TTWID_CACHE:
            return DouyinDownloader._TTWID_CACHE

        try:
            url = "https://ttwid.bytedance.com/ttwid/union/register/"
            data = {
                "region": "cn",
                "aid": 6383,
                "need_t": 1,
                "service": "www.douyin.com",
                "migrate_priority": 0,
                "cb_url_protocol": "https",
                "domain": ".douyin.com",
            }
            resp = self.session.post(url, data=json.dumps(data), timeout=5)
            ttwid = resp.cookies.get("ttwid")
            if ttwid:
                DouyinDownloader._TTWID_CACHE = ttwid
            return ttwid
        except Exception as e:
            logger.warning(f"Failed to get dynamic ttwid: {e}")
            return None

    def fetch_html_data(self):
        for attempt in range(2):
            ttwid = self._get_ttwid()
            if not ttwid:
                ttwid = self.ttwid

            referer_url = f"https://www.douyin.com/video/{self.aweme_id}?previous_page=web_code_link"
            play_url = (
                "https://www.douyin.com/aweme/v1/web/aweme/detail/"
                f"?device_platform=webapp&aid=6383&channel=channel_pc_web&aweme_id={self.aweme_id}&msToken={self.ms_token}"
            )

            new_headers = copy.deepcopy(self.headers)
            new_headers["Referer"] = referer_url
            new_headers["Cookie"] = f"ttwid={ttwid}"
            self.headers["Referer"] = referer_url
            self.headers["Cookie"] = f"ttwid={ttwid}"
            self.headers["Origin"] = "https://www.douyin.com"

            abogus = self.common_utils.get_abogus(play_url, self.common_utils.user_agent)
            url = f"{play_url}&a_bogus={abogus}"

            try:
                response = self.session.get(url, headers=new_headers, verify=False, timeout=5)
                if response.status_code == 200 and response.text:
                    data = response.json()
                    if not data.get("aweme_detail") and attempt == 0:
                        DouyinDownloader._TTWID_CACHE = None
                        continue
                    return data

                if attempt == 0:
                    DouyinDownloader._TTWID_CACHE = None
                    continue
                logger.warning(f"获取抖音详情失败: Status={response.status_code}")
                return None
            except Exception as e:
                logger.error(f"请求抖音详情接口异常: {e}")
                if attempt == 0:
                    DouyinDownloader._TTWID_CACHE = None
                    continue
                return None
        return None

    def get_real_video_url(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get("aweme_detail"):
                return None

            detail = data_dict.get("aweme_detail", {}) or {}
            video = detail.get("video", {}) or {}
            bit_rate = video.get("bit_rate", []) or []

            if not bit_rate:
                return None

            play_addr_list = bit_rate[0].get("play_addr", {}).get("url_list", []) or []
            if len(play_addr_list) < 3:
                return play_addr_list[0] if play_addr_list else None

            return play_addr_list[2]
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse video URL: {e}")
            return None

    def get_title_content(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get("aweme_detail"):
                return None
            return data_dict["aweme_detail"].get("desc", "")
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse title content: {e}")
            return None

    def get_cover_photo_url(self):
        try:
            data_dict = self.data
            if not data_dict:
                return None

            detail = data_dict.get("aweme_detail") or {}

            video_cover = None
            video_data = detail.get("video") or {}
            if video_data and "dynamic_cover" in video_data:
                url_list = video_data["dynamic_cover"].get("url_list") or []
                if url_list:
                    video_cover = url_list[0]

            images_cover = None
            images_list = detail.get("images") or []
            if images_list:
                first_img = images_list[0] or {}
                url_list = first_img.get("url_list") or []
                if url_list:
                    images_cover = url_list[0]

            play_cover = video_cover or images_cover
            if not play_cover:
                logger.info("No cover URL found in both video and images.")

            return play_cover
        except Exception as e:
            logger.warning(f"Failed to parse cover URL: {e}")
            return None

    def get_audio_url(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get("aweme_detail"):
                return None
            detail = data_dict.get("aweme_detail") or {}
            music = detail.get("music") or {}
            play_url = music.get("play_url") or {}
            url_list = play_url.get("url_list") or []
            if url_list:
                return url_list[0]
            return None
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse background music: {e}")
            return None

    def get_author_info(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get("aweme_detail"):
                return None

            author = data_dict["aweme_detail"].get("author") or {}
            if not author:
                return None

            avatar_thumb = author.get("avatar_thumb") or {}
            avatar_url_list = avatar_thumb.get("url_list") or [None]

            return {
                "nickname": author.get("nickname", ""),
                "author_id": author.get("unique_id") or author.get("short_id", ""),
                "avatar": avatar_url_list[0],
            }
        except Exception as e:
            logger.warning(f"Failed to parse author info: {e}")
            return None

    def get_image_list(self):
        """提取图文内容中的高清图集地址。"""
        try:
            data_dict = self.data
            if not data_dict or "aweme_detail" not in data_dict:
                return []

            images = data_dict["aweme_detail"].get("images") or []
            if not images:
                images = data_dict["aweme_detail"].get("image_list") or []

            image_urls = []
            for img in images:
                if not img:
                    continue
                urls = img.get("url_list")
                if urls and isinstance(urls, list) and len(urls) > 0:
                    image_urls.append(urls[-1])

            return image_urls
        except Exception as e:
            logger.warning(f"Failed to parse image list: {e}")
            return []
