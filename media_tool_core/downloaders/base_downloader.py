import os
import uuid

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, RequestException
from urllib3.util.retry import Retry

from media_tool_core.configs.general_constants import SAVE_IMAGE_PATH, SAVE_VIDEO_PATH
from media_tool_core.configs.logging_config import get_logger

logger = get_logger(__name__)


class BaseDownloader:
    def __init__(self, real_url):
        self.real_url = real_url
        self.headers = None
        self.html_content = None
        self.session = requests.Session()

    def get_real_video_url(self):
        raise NotImplementedError

    def get_title_content(self):
        raise NotImplementedError

    def get_cover_photo_url(self):
        raise NotImplementedError

    def get_author_info(self):
        raise NotImplementedError

    def get_audio_url(self):
        return None

    def get_image_list(self):
        return []

    def fetch_html_content(self):
        try:
            response = self.session.get(self.real_url, headers=self.headers, timeout=5)
            response.raise_for_status()
            self.html_content = response.text
            return self.html_content
        except requests.RequestException as exc:
            logger.error("Failed to get the page: %s, error: %s", self.real_url, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error while fetching %s: %s", self.real_url, exc)
            return None

    @staticmethod
    def parse_html_data(html_content, pattern):
        page_obj = BeautifulSoup(html_content, "lxml")
        script_tags = page_obj.find_all("script")
        for script in script_tags:
            if script.string:
                match = pattern.search(script.string)
                if match:
                    json_data = match.group(1)
                    json_data = json_data.rstrip(";")
                    json_data = json_data.replace("undefined", "null")
                    return json_data
        logger.error("Video object not found")
        return None

    @staticmethod
    def mkdir(folder):
        if not os.path.exists(folder):
            os.makedirs(folder, 0o777)
            return True
        return False

    def download_and_save(self, folder, url, file_extension):
        BaseDownloader.mkdir(folder)
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session = requests.Session()
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        try:
            response = session.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to download the resource: %s", exc)
            raise

        filename = os.path.join(folder, f"{uuid.uuid4()}.{file_extension}")
        full_name = os.path.abspath(filename)
        try:
            with open(full_name, "wb") as file_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file_obj.write(chunk)
        except (ChunkedEncodingError, IOError) as exc:
            logger.error("Failed to save the resource: %s", exc)
            raise
        return full_name

    def download_and_save_video(self):
        video_url = self.get_real_video_url()
        logger.debug("视频下载地址: %s", video_url)
        return self.download_and_save(SAVE_VIDEO_PATH, video_url, "mp4")

    def download_and_save_image(self):
        photo_url = self.get_cover_photo_url()
        if photo_url:
            logger.debug("封面下载地址: %s", photo_url)
            return self.download_and_save(SAVE_IMAGE_PATH, photo_url, "jpg")
        logger.debug("未获取到封面下载地址")
        return None
