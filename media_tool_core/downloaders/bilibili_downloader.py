import concurrent.futures
import os
import random
import re
import subprocess
import uuid

import requests

from media_tool_core.configs.general_constants import DOMAIN, SAVE_VIDEO_PATH, USER_AGENT_PC
from media_tool_core.configs.logging_config import get_logger
from media_tool_core.downloaders.base_downloader import BaseDownloader
from media_tool_core.utils.ffmpeg_utils import require_ffmpeg_binary

logger = get_logger(__name__)


class BilibiliDownloader(BaseDownloader):
    """通过 Bilibili 官方 API 获取视频信息与可播放资源。"""

    API_VIEW = "https://api.bilibili.com/x/web-interface/view"
    API_PLAYURL = "https://api.bilibili.com/x/player/playurl"

    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "User-Agent": random.choice(USER_AGENT_PC),
            "referer": "https://www.bilibili.com/",
        }
        self.bvid = self._extract_bvid(real_url)
        self.video_info = self._fetch_video_info()
        self.play_info = self._fetch_play_info()

    @staticmethod
    def _extract_bvid(url):
        match = re.search(r"(BV[a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        logger.error(f"无法从 URL 中提取 BV 号: {url}")
        return None

    def _fetch_video_info(self):
        """获取标题、封面、作者与 pages 等基础信息。"""
        if not self.bvid:
            return {}
        try:
            resp = self.session.get(
                self.API_VIEW,
                params={"bvid": self.bvid},
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                logger.debug(f"B站视频信息获取成功: {self.bvid}")
                return result.get("data", {})

            logger.error(f"B站视频信息接口返回错误: code={result.get('code')}, message={result.get('message')}")
            return {}
        except requests.RequestException as e:
            logger.error(f"B站 API 视频信息请求失败: {e}")
            return {}

    def _fetch_play_info(self):
        """获取 DASH 播放流地址。"""
        cid = self._get_cid()
        if not self.bvid or not cid:
            return {}
        try:
            resp = self.session.get(
                self.API_PLAYURL,
                params={
                    "bvid": self.bvid,
                    "cid": cid,
                    "qn": 80,
                    "fnval": 16,
                },
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                logger.debug(f"B站 DASH 播放流获取成功: {self.bvid}")
                return result.get("data", {})

            logger.error(f"B站 playurl 接口返回错误: code={result.get('code')}, message={result.get('message')}")
            return {}
        except requests.RequestException as e:
            logger.error(f"B站 API playurl 请求失败: {e}")
            return {}

    def _get_cid(self):
        pages = self.video_info.get("pages", [])
        if pages:
            return pages[0].get("cid")
        return None

    def get_video_m4s_url(self):
        try:
            videos = self.play_info.get("dash", {}).get("video", [])
            if videos:
                return videos[0].get("baseUrl")
            return None
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Bilibili video URL: {e}")
            return None

    def get_audio_m4s_url(self):
        try:
            audios = self.play_info.get("dash", {}).get("audio", [])
            if audios:
                return audios[0].get("baseUrl")
            return None
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Bilibili audio URL: {e}")
            return None

    def get_audio_url(self):
        """下载音频流并转封装为 m4a。"""
        audio_url = self.get_audio_m4s_url()
        if not audio_url:
            return None

        audio_m4s_path = self.download_and_save(SAVE_VIDEO_PATH, audio_url, "m4s")
        if not audio_m4s_path:
            logger.error("下载 B 站音频 m4s 失败")
            return None

        output_filename = f"{uuid.uuid4()}_audio.m4a"
        output_path = os.path.join(SAVE_VIDEO_PATH, output_filename)

        ffmpeg_binary = require_ffmpeg_binary()
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            audio_m4s_path,
            "-c:a",
            "copy",
            output_path,
        ]

        try:
            logger.debug(f"开始执行 FFmpeg 音频转封装: {' '.join(command)}")
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return f"{DOMAIN}/static/videos/{output_filename}"
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFmpeg 音频转封装失败: {error_message}")
            return None
        finally:
            if os.path.exists(audio_m4s_path):
                os.remove(audio_m4s_path)

    def get_title_content(self):
        return self.video_info.get("title", "")

    def get_cover_photo_url(self):
        return self.video_info.get("pic", "")

    def get_author_info(self):
        owner = self.video_info.get("owner", {})
        author_info = {
            "nickname": owner.get("name", ""),
            "author_id": str(owner.get("mid", "")),
            "avatar": owner.get("face", ""),
        }
        if author_info["avatar"] and author_info["avatar"].startswith("//"):
            author_info["avatar"] = "https:" + author_info["avatar"]
        return author_info

    def get_real_video_url(self):
        """获取单文件 mp4 方案，并下载到本地静态目录后返回地址。"""
        cid = self._get_cid()
        if not self.bvid or not cid:
            logger.error("无法获取 BV 号或 cid，跳过 durl 获取")
            return None
        try:
            resp = self.session.get(
                self.API_PLAYURL,
                params={
                    "bvid": self.bvid,
                    "cid": cid,
                    "qn": 64,
                    "fnval": 0,
                },
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                durls = result.get("data", {}).get("durl", [])
                if durls:
                    cdn_url = durls[0].get("url")
                    logger.debug(f"B站 durl 获取成功，准备下载到本地: {self.bvid}")
                    saved_path = self.download_and_save(SAVE_VIDEO_PATH, cdn_url, "mp4")
                    if saved_path:
                        filename = os.path.basename(saved_path)
                        return f"{DOMAIN}/static/videos/{filename}"
                    return None
            logger.error(f"B站 durl 接口返回错误: {result.get('message')}")
            return None
        except requests.RequestException as e:
            logger.error(f"B站 durl 请求失败: {e}")
            return None

    def get_real_video_url_hd(self):
        """下载 DASH 视频流和音频流，合并生成 mp4。"""
        video_url = self.get_video_m4s_url()
        audio_url = self.get_audio_m4s_url()

        if not video_url or not audio_url:
            logger.error("无法获取 B 站 DASH 视频流或音频流")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_video = executor.submit(self.download_and_save, SAVE_VIDEO_PATH, video_url, "m4s")
            future_audio = executor.submit(self.download_and_save, SAVE_VIDEO_PATH, audio_url, "m4s")
            video_m4s_path = future_video.result()
            audio_m4s_path = future_audio.result()

        if not video_m4s_path or not audio_m4s_path:
            logger.error("下载 B 站 DASH m4s 文件失败")
            return None

        output_filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(SAVE_VIDEO_PATH, output_filename)

        ffmpeg_binary = require_ffmpeg_binary()
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            video_m4s_path,
            "-i",
            audio_m4s_path,
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            output_path,
        ]

        try:
            logger.debug(f"开始执行 FFmpeg 合并视频音频: {' '.join(command)}")
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return f"{DOMAIN}/static/videos/{output_filename}"
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFmpeg 合并失败: {error_message}")
            return None
        finally:
            if os.path.exists(video_m4s_path):
                os.remove(video_m4s_path)
            if os.path.exists(audio_m4s_path):
                os.remove(audio_m4s_path)
