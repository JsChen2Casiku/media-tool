# ======= 鐜閰嶇疆寮€濮嬶細灏嗛」鐩牴鐩綍娣诲姞鍒扮郴缁熻矾寰勶紝褰撳墠鑴氭湰鍙祴璇?=======

from pathlib import Path
import sys
# 鑾峰彇褰撳墠鏂囦欢鐨勭粷瀵硅矾寰勶紝骞跺畾浣嶈嚦鍚戜笂鎺ㄤ袱绾х殑椤圭洰鏍圭洰褰?
root_dir = str(Path(__file__).resolve().parents[2])
# 濡傛灉鏍圭洰褰曚笉鍦ㄧ郴缁熸悳绱㈣矾寰勪腑锛屽垯鍔ㄦ€佹坊鍔狅紝浠ョ‘淇濊法妯″潡瀵煎叆锛圛mport锛夋甯稿伐浣?
if root_dir not in sys.path:
    sys.path.append(root_dir)

# ========================= 鐜閰嶇疆缁撴潫 =========================


import json
import urllib3
import warnings
import copy
from media_tool_core.utils.web_fetcher import UrlParser
from media_tool_core.utils.douyin_utils.bogus_sign_utils import CommonUtils
from media_tool_core.configs.logging_config import get_logger
logger = get_logger(__name__)
from media_tool_core.downloaders.base_downloader import BaseDownloader

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


class DouyinDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.common_utils = CommonUtils()
        self.headers = {
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'Accept': 'application/json, text/plain, */*',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': self.common_utils.user_agent,
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.ms_token = self.common_utils.get_ms_token()
        self.ttwid = '1%7CvDWCB8tYdKPbdOlqwNTkDPhizBaV9i91KjYLKJbqurg%7C1723536402%7C314e63000decb79f46b8ff255560b29f4d8c57352dad465b41977db4830b4c7e'
        self.webid = '7307457174287205926'
        self.fetch_html_content()
        self.aweme_id = UrlParser.get_video_id(self.real_url)
        self.data = self.fetch_html_data()

    _TTWID_CACHE = None

    def _get_ttwid(self):
        """
        鍔ㄦ€佽幏鍙?ttwid锛屽鍔犱簡绫荤骇鍒殑缂撳瓨浠ュ噺灏戦噸澶嶈姹?
        """
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
                "domain": ".douyin.com"
            }
            # 浣跨敤 instance session
            resp = self.session.post(url, data=json.dumps(data), timeout=5)
            ttwid = resp.cookies.get('ttwid')
            if ttwid:
                DouyinDownloader._TTWID_CACHE = ttwid
            return ttwid
        except Exception as e:
            logger.warning(f"Failed to get dynamic ttwid: {e}")
            return None

    def fetch_html_data(self):
        # 灏濊瘯浣跨敤缂撳瓨鐨?ttwid锛屽苟鍦ㄥけ璐ユ椂閲嶈瘯涓€娆★紙鍒锋柊 ttwid锛?
        for attempt in range(2):
            ttwid = self._get_ttwid()
            if not ttwid:
                ttwid = '1%7CvDWCB8tYdKPbdOlqwNTkDPhizBaV9i91KjYLKJbqurg%7C1723536402%7C314e63000decb79f46b8ff255560b29f4d8c57352dad465b41977db4830b4c7e'

            referer_url = f"https://www.douyin.com/video/{self.aweme_id}?previous_page=web_code_link"
            play_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?device_platform=webapp&aid=6383&channel=channel_pc_web&aweme_id={self.aweme_id}&msToken={self.ms_token}"
            
            new_headers = copy.deepcopy(self.headers)
            new_headers['Referer'] = referer_url
            new_headers['Cookie'] = f"ttwid={ttwid}"
            self.headers['Referer'] = referer_url
            self.headers['Cookie'] = f"ttwid={ttwid}"
            self.headers['Origin'] = "https://www.douyin.com"
             
            abogus = self.common_utils.get_abogus(play_url, self.common_utils.user_agent)
            url = f"{play_url}&a_bogus={abogus}"
            
            try:
                response = self.session.get(url, headers=new_headers, verify=False, timeout=5)
                if response.status_code == 200 and response.text:
                    data = response.json()
                    # 濡傛灉杩斿洖缁撴灉涓病鏈夋牳蹇冨瓧娈碉紝璇存槑 ttwid 鍙兘鍦ㄦ湇鍔″櫒绔凡澶辨晥锛屾竻绌虹紦瀛橀噸璇?
                    if not data.get('aweme_detail') and attempt == 0:
                        DouyinDownloader._TTWID_CACHE = None
                        continue
                    return data
                else:
                    if attempt == 0:
                        DouyinDownloader._TTWID_CACHE = None
                        continue
                    logger.warning(f"鑾峰彇鎶栭煶瑙嗛璇︽儏澶辫触: Status={response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"璇锋眰鎶栭煶璇︽儏鎺ュ彛寮傚父: {e}")
                if attempt == 0:
                    DouyinDownloader._TTWID_CACHE = None
                    continue
                return None
        return None

    def get_real_video_url(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get('aweme_detail'):
                return None
            
            detail = data_dict.get('aweme_detail', {}) or {}
            video = detail.get('video', {}) or {}
            bit_rate = video.get('bit_rate', []) or []
            
            if not bit_rate:
                return None
                
            play_addr_list = bit_rate[0].get('play_addr', {}).get('url_list', []) or []
            if len(play_addr_list) < 3:
                return play_addr_list[0] if play_addr_list else None
                
            # play_addr_list[0]:涓籆DN鑺傜偣; play_addr_list[1]:澶囩敤CDN鑺傜偣; play_addr_list[2]:鎶栭煶瀹樻柟鐨勬簮绔橴RL
            play_addr = play_addr_list[2]
            return play_addr
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse video URL: {e}")
            return None

    def get_title_content(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get('aweme_detail'):
                return None
            title_content = data_dict['aweme_detail'].get('desc', '')
            return title_content
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse title content: {e}")
            return None

    def get_cover_photo_url(self):
        try:
            data_dict = self.data
            if not data_dict:
                return None
            
            # 浣跨敤 or {} 纭繚 detail 涓嶆槸 None
            detail = data_dict.get('aweme_detail') or {}
            
            # 1. 灏濊瘯鑾峰彇瑙嗛鍔ㄦ€佸皝闈?
            video_cover = None
            video_data = detail.get('video') or {}
            if video_data and 'dynamic_cover' in video_data:
                url_list = video_data['dynamic_cover'].get('url_list') or []
                if url_list:
                    video_cover = url_list[0]
            
            # 2. 灏濊瘯鑾峰彇鍥鹃泦灏侀潰 (濡傛灉瑙嗛灏侀潰涓嶅瓨鍦?
            images_cover = None
            images_list = detail.get('images') or []
            if images_list and len(images_list) > 0:
                first_img = images_list[0] or {}
                url_list = first_img.get('url_list') or []
                if url_list:
                    images_cover = url_list[0]
            
            # 3. 浼樺厛绾ч€昏緫锛氭湁瑙嗛灏侀潰浼樺厛鐢ㄨ棰戯紝鍚﹀垯鐢ㄥ浘闆嗗皝闈?
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
            if not data_dict or not data_dict.get('aweme_detail'):
                return None
            detail = data_dict.get('aweme_detail') or {}
            music = detail.get('music') or {}
            play_url = music.get('play_url') or {}
            url_list = play_url.get('url_list') or []
            if url_list:
                return url_list[0]
            return None
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse background music: {e}")
            return None

    def get_author_info(self):
        try:
            data_dict = self.data
            if not data_dict or not data_dict.get('aweme_detail'):
                return None
                
            author = (data_dict['aweme_detail'].get('author') or {})
            if not author:
                return None
                
            # 1. 鎶栭煶鍙烽€昏緫锛氫紭鍏堝彇 unique_id (鑷畾涔夊彿)锛屾病鏈夊垯鍙?short_id
            # 2. 澶村儚閫昏緫锛氬畨鍏ㄥ彇 url_list 鐨勭涓€涓厓绱?
            avatar_thumb = author.get('avatar_thumb') or {}
            avatar_url_list = avatar_thumb.get('url_list') or [None]
            
            return {
                "nickname": author.get('nickname', ''),
                "author_id": author.get('unique_id') or author.get('short_id', ''),
                "avatar": avatar_url_list[0]
            }
        except Exception as e:
            logger.warning(f"Failed to parse author info: {e}")
            return None

    def get_image_list(self):
        """
        閽堝 aweme_type 68 鐨勫浘鏂囩瑪璁帮紝鎻愬彇鎵€鏈夐珮娓呭浘鐗囬摼鎺?
        """
        try:
            data_dict = self.data
            if not data_dict or 'aweme_detail' not in data_dict:
                return []

            # 1. 鎶栭煶鍥炬枃绗旇鐨勫浘鐗囧瓨鍌ㄥ湪 images 瀛楁涓?
            images = data_dict['aweme_detail'].get('images') or []
            if not images:
                # 鍏滃簳锛氭湁浜涚増鏈彲鑳藉湪 image_list 瀛楁
                images = data_dict['aweme_detail'].get('image_list') or []

            image_urls = []
            for img in images:
                if not img:
                    continue
                # 鈿狅笍 娉ㄦ剰锛歞ownload_url_list 鍖呭惈甯︽按鍗扮殑鍥剧墖锛?
                # url_list 鎵嶆槸鏃犳按鍗扮殑鍘熷鍥剧墖閾炬帴锛堝凡閫氳繃 f2 绛変富娴侀」鐩獙璇侊級
                # url_list 涓渶鍚庝竴涓厓绱犻€氬父鏄渶楂樿川閲忕殑 CDN 閾炬帴
                urls = img.get('url_list')

                if urls and isinstance(urls, list) and len(urls) > 0:
                    # 浼樺厛鍙栨渶鍚庝竴涓?URL锛堥€氬父鏄渶楂樿川閲忕殑婧愮珯 CDN锛?
                    image_urls.append(urls[-1])

            return image_urls

        except Exception as e:
            logger.warning(f"Failed to parse image list: {e}")
            return []


