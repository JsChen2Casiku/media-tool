from importlib import import_module

from media_tool_core.configs.general_constants import get_platform_label


class DownloaderFactory:
    platform_to_downloader = {
        "xiaohongshu": ("media_tool_core.downloaders.xiaohongshu_downloader", "XiaohongshuDownloader"),
        "douyin": ("media_tool_core.downloaders.douyin_downloader", "DouyinDownloader"),
        "kuaishou": ("media_tool_core.downloaders.kuaishou_downloader", "KuaishouDownloader"),
        "bilibili": ("media_tool_core.downloaders.bilibili_downloader", "BilibiliDownloader"),
        "haokan": ("media_tool_core.downloaders.haokan_downloader", "HaokanDownloader"),
        "weishi": ("media_tool_core.downloaders.weishi_downloader", "WeishiDownloader"),
        "pearvideo": ("media_tool_core.downloaders.lishipin_downloader", "LishipinDownloader"),
        "pipigaoxiao": ("media_tool_core.downloaders.pipigaoxiao_downloader", "PipigaoxiaoDownloader"),
        "acfun": ("media_tool_core.downloaders.acfun_downloader", "AcfunDownloader"),
        "instagram": ("media_tool_core.downloaders.instagram_downloader", "InstagramDownloader"),
        "tiktok": ("media_tool_core.downloaders.tiktok_downloader", "TiktokDownloader"),
        "twitter": ("media_tool_core.downloaders.twitter_downloader", "TwitterDownloader"),
        "weibo": ("media_tool_core.downloaders.weibo_downloader", "WeiboDownloader"),
        "ixigua": ("media_tool_core.downloaders.xigua_downloader", "XiguaDownloader"),
        "youtube": ("media_tool_core.downloaders.youtube_downloader", "YoutubeDownloader"),
        "zhihu": ("media_tool_core.downloaders.zhihu_downloader", "ZhihuDownloader"),
    }

    @staticmethod
    def create_downloader(platform, real_url):
        target = DownloaderFactory.platform_to_downloader.get(platform)
        if not target:
            raise ValueError(f"不支持的平台: {get_platform_label(platform)}")
        module_name, class_name = target
        module = import_module(module_name)
        downloader_class = getattr(module, class_name)
        return downloader_class(real_url)
