import re
import os
import uuid
import random
import requests
import subprocess
import concurrent.futures
from media_tool_core.downloaders.base_downloader import BaseDownloader
from media_tool_core.configs.general_constants import USER_AGENT_PC, SAVE_VIDEO_PATH, DOMAIN
from media_tool_core.configs.logging_config import get_logger
logger = get_logger(__name__)


class BilibiliDownloader(BaseDownloader):
    """
    B绔欎笅杞藉櫒 鈥斺€?閫氳繃瀹樻柟 API 鑾峰彇瑙嗛淇℃伅鍜?DASH 娴佸湴鍧€銆?

    璋冪敤閾捐矾锛?
    1. 浠?URL 涓彁鍙?BV 鍙?
    2. 璋冪敤 /x/web-interface/view 鎺ュ彛鑾峰彇瑙嗛鍏冧俊鎭紙鏍囬銆佸皝闈€佷綔鑰呫€乧id锛?
    3. 璋冪敤 /x/player/playurl 鎺ュ彛鑾峰彇 DASH 瑙嗛娴佸拰闊抽娴佺殑涓嬭浇鍦板潃
    4. 骞跺彂涓嬭浇 video.m4s + audio.m4s锛屼娇鐢?FFmpeg 鍚堝苟涓?mp4

    鐩告瘮鏃х増鐖彇缃戦〉 HTML 鐨勬柟妗堬紝API 鏂规鐨勪紭鍔匡細
    - 涓嶅彈 B 绔欓拡瀵规暟鎹腑蹇?IP 鐨勭綉椤?WAF (412) 鎷︽埅
    - 杩斿洖缁撴瀯鍖?JSON锛屾棤闇€ BeautifulSoup 瑙ｆ瀽 HTML
    - 鏇寸ǔ瀹氾紝涓嶅彈鍓嶇椤甸潰缁撴瀯鍙樺寲褰卞搷
    """

    # B绔欏畼鏂?API 绔偣
    API_VIEW = 'https://api.bilibili.com/x/web-interface/view'
    API_PLAYURL = 'https://api.bilibili.com/x/player/playurl'

    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            'User-Agent': random.choice(USER_AGENT_PC),
            'referer': 'https://www.bilibili.com/'
        }
        self.bvid = self._extract_bvid(real_url)
        # 閫氳繃 API 鑾峰彇瑙嗛鍏冧俊鎭?
        self.video_info = self._fetch_video_info()
        # 閫氳繃 API 鑾峰彇 DASH 娴佸湴鍧€
        self.play_info = self._fetch_play_info()

    @staticmethod
    def _extract_bvid(url):
        """浠?URL 涓彁鍙?BV 鍙凤紝濡?BV1df421v7xm"""
        match = re.search(r'(BV[a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        logger.error(f"鏃犳硶浠?URL 涓彁鍙?BV 鍙? {url}")
        return None

    def _fetch_video_info(self):
        """
        璋冪敤 /x/web-interface/view 鎺ュ彛鑾峰彇瑙嗛鍏冧俊鎭€?
        杩斿洖 data 瀛楀吀锛屽寘鍚?title銆乸ic銆乷wner銆乸ages锛堝惈 cid锛夌瓑銆?
        """
        if not self.bvid:
            return {}
        try:
            resp = self.session.get(
                self.API_VIEW,
                params={'bvid': self.bvid},
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') == 0:
                logger.debug(f"B绔?API 瑙嗛淇℃伅鑾峰彇鎴愬姛: {self.bvid}")
                return result.get('data', {})
            else:
                logger.error(f"B绔?API 杩斿洖閿欒: code={result.get('code')}, message={result.get('message')}")
                return {}
        except requests.RequestException as e:
            logger.error(f"B绔?API 瑙嗛淇℃伅璇锋眰澶辫触: {e}")
            return {}

    def _fetch_play_info(self):
        """
        璋冪敤 /x/player/playurl 鎺ュ彛鑾峰彇 DASH 娴佸湴鍧€銆?
        闇€瑕?bvid 鍜?cid 涓や釜鍙傛暟锛宑id 浠?video_info 涓幏鍙栥€?
        fnval=16 琛ㄧず璇锋眰 DASH 鏍煎紡锛宷n=80 琛ㄧず 1080P 鐢昏川銆?
        """
        cid = self._get_cid()
        if not self.bvid or not cid:
            return {}
        try:
            resp = self.session.get(
                self.API_PLAYURL,
                params={
                    'bvid': self.bvid,
                    'cid': cid,
                    'qn': 80,
                    'fnval': 16  # DASH 鏍煎紡
                },
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') == 0:
                logger.debug(f"B绔?API DASH 娴佸湴鍧€鑾峰彇鎴愬姛: {self.bvid}")
                return result.get('data', {})
            else:
                logger.error(f"B绔?API playurl 杩斿洖閿欒: code={result.get('code')}, message={result.get('message')}")
                return {}
        except requests.RequestException as e:
            logger.error(f"B绔?API playurl 璇锋眰澶辫触: {e}")
            return {}

    def _get_cid(self):
        """浠?video_info 涓彁鍙栫涓€涓垎P鐨?cid"""
        pages = self.video_info.get('pages', [])
        if pages:
            return pages[0].get('cid')
        return None

    def get_video_m4s_url(self):
        try:
            videos = self.play_info.get('dash', {}).get('video', [])
            if videos:
                return videos[0].get('baseUrl')
            return None
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Bilibili video URL: {e}")
            return None

    def get_audio_m4s_url(self):
        try:
            audios = self.play_info.get('dash', {}).get('audio', [])
            if audios:
                return audios[0].get('baseUrl')
            return None
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Bilibili audio URL: {e}")
            return None

    def get_audio_url(self):
        """
        鑾峰彇鐙珛鐨勯煶棰戦摼鎺ワ細涓嬭浇 m4s 闊抽娴佺紦瀛橈紝骞惰浆灏佽涓洪€氱敤 m4a锛岃繑鍥炴湇鍔″櫒鍙闂湴鍧€
        """
        audio_url = self.get_audio_m4s_url()
        if not audio_url:
            return None
            
        audio_m4s_path = self.download_and_save(SAVE_VIDEO_PATH, audio_url, "m4s")
        if not audio_m4s_path:
            logger.error("涓嬭浇 B 绔欓煶棰?m4s 鏂囦欢澶辫触")
            return None

        output_filename = f"{uuid.uuid4()}_audio.m4a"
        output_path = os.path.join(SAVE_VIDEO_PATH, output_filename)

        command = [
            "ffmpeg",
            "-y",
            "-i", audio_m4s_path,
            "-c:a", "copy",
            output_path
        ]

        try:
            logger.debug(f"姝ｅ湪浣跨敤 FFmpeg 杞崲鎻愬彇闊抽: {' '.join(command)}")
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return f"{DOMAIN}/static/videos/{output_filename}"
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFmpeg 杞崲闊抽澶辫触: {error_message}")
            return None
        finally:
            if os.path.exists(audio_m4s_path):
                os.remove(audio_m4s_path)

    def get_title_content(self):
        return self.video_info.get('title', '')

    def get_cover_photo_url(self):
        return self.video_info.get('pic', '')

    def get_author_info(self):
        owner = self.video_info.get('owner', {})
        author_info = {
            'nickname': owner.get('name', ''),
            'author_id': str(owner.get('mid', '')),
            'avatar': owner.get('face', '')
        }
        # B绔欑殑澶村儚 URL 缁忓父浠?// 寮€澶达紝缂哄皯鍗忚澶达紝鍋氫釜鍏煎澶勭悊
        if author_info['avatar'] and author_info['avatar'].startswith('//'):
            author_info['avatar'] = 'https:' + author_info['avatar']
        return author_info

    def get_real_video_url(self):
        """
        durl 鍗曟枃浠舵柟妗堬紙480P锛夛細鑾峰彇鍖呭惈瑙嗛+闊抽鐨勫崟涓?mp4 鏂囦欢閾炬帴锛?
        涓嬭浇鍒版湇鍔″櫒鍚庤繑鍥炶嚜鏈夊煙鍚嶇殑鍙挱鏀鹃摼鎺ャ€?
        B绔?CDN 鏈?Referer 闃茬洍閾惧拰閾炬帴鏃舵晥闄愬埗锛屾棤娉曠洿鎺ヨ繑鍥?CDN 鍘熷閾炬帴銆?
        """
        cid = self._get_cid()
        if not self.bvid or not cid:
            logger.error("鏃犳硶鑾峰彇 BV 鍙锋垨 cid锛岃烦杩?durl 鑾峰彇")
            return None
        try:
            resp = self.session.get(
                self.API_PLAYURL,
                params={
                    'bvid': self.bvid,
                    'cid': cid,
                    'qn': 64,
                    'fnval': 0  # fnval=0 杩斿洖 durl 鏍煎紡锛堝崟鏂囦欢锛?
                },
                headers=self.headers,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') == 0:
                durls = result.get('data', {}).get('durl', [])
                if durls:
                    cdn_url = durls[0].get('url')
                    logger.debug(f"B绔?durl 鍗曟枃浠堕摼鎺ヨ幏鍙栨垚鍔? {self.bvid}")
                    # 涓嬭浇鍒版湇鍔″櫒锛岃繑鍥炶嚜鏈夊煙鍚嶉摼鎺?
                    saved_path = self.download_and_save(SAVE_VIDEO_PATH, cdn_url, "mp4")
                    if saved_path:
                        filename = os.path.basename(saved_path)
                        return f"{DOMAIN}/static/videos/{filename}"
                    return None
            logger.error(f"B绔?durl 鑾峰彇澶辫触: {result.get('message')}")
            return None
        except requests.RequestException as e:
            logger.error(f"B绔?durl 璇锋眰澶辫触: {e}")
            return None

    def get_real_video_url_hd(self):
        """
        DASH 楂樻竻鏂规锛?080P锛夛細涓嬭浇瑙嗛鐨?m4s 鍜岄煶棰戠殑 m4s 鏂囦欢锛?
        浣跨敤 FFmpeg 鍚堝苟涓?mp4锛屼繚瀛樺埌 static/videos 涓紝骞惰繑鍥炴湇鍔″櫒鍙闂殑瑙嗛閾炬帴銆?
        """
        video_url = self.get_video_m4s_url()
        audio_url = self.get_audio_m4s_url()

        if not video_url or not audio_url:
            logger.error("鏃犳硶鑾峰彇 B 绔欒棰戞垨闊抽閾炬帴 m4s 鍦板潃")
            return None

        # 骞跺彂涓嬭浇 m4s 鍙戞尌鏈€澶х綉缁滃甫瀹?
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_video = executor.submit(self.download_and_save, SAVE_VIDEO_PATH, video_url, "m4s")
            future_audio = executor.submit(self.download_and_save, SAVE_VIDEO_PATH, audio_url, "m4s")

            video_m4s_path = future_video.result()
            audio_m4s_path = future_audio.result()

        if not video_m4s_path or not audio_m4s_path:
            logger.error("涓嬭浇 B 绔欒棰戞垨闊抽 m4s 鏂囦欢澶辫触")
            return None

        # 闅忔満鐢熸垚鏈€缁堢殑 mp4 鏂囦欢鍚?
        output_filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(SAVE_VIDEO_PATH, output_filename)

        # 浣跨敤 ffmpeg 鎷兼帴
        command = [
            "ffmpeg",
            "-y",  # overwrite output file if it exists
            "-i", video_m4s_path,
            "-i", audio_m4s_path,
            "-c:v", "copy",
            "-c:a", "copy",
            output_path
        ]

        try:
            logger.debug(f"姝ｅ湪浣跨敤 FFmpeg 鍚堝苟瑙嗛鍜岄煶棰? {' '.join(command)}")
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # 鎷兼帴鏈嶅姟鍣ㄥ湴鍧€
            server_video_url = f"{DOMAIN}/static/videos/{output_filename}"
            return server_video_url
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFmpeg 鍚堝苟澶辫触: {error_message}")
            return None
        finally:
            # 鏃犺鎴愬姛鎴栧け璐ワ紝閮芥竻鐞嗕复鏃?m4s 鏂囦欢
            if os.path.exists(video_m4s_path):
                os.remove(video_m4s_path)
            if os.path.exists(audio_m4s_path):
                os.remove(audio_m4s_path)



