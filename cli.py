import argparse
import json

from media_tool_core.schemas import DownloadRequest, ExtractRequest
from media_tool_core.services.media_service import download_media, extract_transcript, parse_media


def build_parser():
    parser = argparse.ArgumentParser(description="media-tool：短视频解析、下载与文案提取工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="解析媒体信息")
    parse_cmd.add_argument("--text", "-t", required=True, help="分享文案或链接")

    download_cmd = subparsers.add_parser("download", help="下载视频、封面和图集")
    download_cmd.add_argument("--text", "-t", required=True, help="分享文案或链接")
    download_cmd.add_argument("--output-dir", "-o", help="输出目录")
    download_cmd.add_argument("--skip-video", action="store_true", help="不下载视频")
    download_cmd.add_argument("--skip-cover", action="store_true", help="不下载封面")
    download_cmd.add_argument("--skip-images", action="store_true", help="不下载图集")

    extract_cmd = subparsers.add_parser("extract", help="提取视频文案")
    extract_cmd.add_argument("--text", "-t", required=True, help="分享文案或链接")
    extract_cmd.add_argument("--output-dir", "-o", help="输出目录")
    extract_cmd.add_argument("--backend", choices=["openai", "funasr", "doubaoime"], help="转写后端")
    extract_cmd.add_argument("--api-base", help="OpenAI 兼容接口地址")
    extract_cmd.add_argument("--api-key", help="接口密钥")
    extract_cmd.add_argument("--model", help="模型名称")
    extract_cmd.add_argument("--funasr-vad-model", help="FunASR VAD 模型名")
    extract_cmd.add_argument("--funasr-punc-model", help="FunASR 标点模型名")
    extract_cmd.add_argument("--funasr-device", help="FunASR 设备，例如 auto、cpu、cuda:0")
    extract_cmd.add_argument("--doubaoime-credential-path", help="豆包输入法 ASR 凭据缓存文件路径")
    extract_cmd.add_argument("--doubaoime-device-id", help="豆包输入法 ASR 设备 ID")
    extract_cmd.add_argument("--doubaoime-token", help="豆包输入法 ASR Token")
    extract_cmd.add_argument(
        "--doubaoime-disable-punctuation",
        action="store_true",
        help="关闭豆包输入法 ASR 自动标点",
    )
    extract_cmd.add_argument("--save-video", action="store_true", help="转写完成后保留视频")
    extract_cmd.add_argument("--save-cover", action="store_true", help="转写完成后保留封面")
    extract_cmd.add_argument("--save-images", action="store_true", help="转写完成后保留图集")
    extract_cmd.add_argument("--skip-transcript", action="store_true", help="不保存 transcript.md")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        print(json.dumps(parse_media(args.text), ensure_ascii=False, indent=2))
        return

    if args.command == "download":
        payload = DownloadRequest(
            text=args.text,
            output_dir=args.output_dir,
            save_video=not args.skip_video,
            save_cover=not args.skip_cover,
            save_images=not args.skip_images,
        )
        print(json.dumps(download_media(payload), ensure_ascii=False, indent=2))
        return

    if args.command == "extract":
        payload = ExtractRequest(
            text=args.text,
            output_dir=args.output_dir,
            backend=args.backend,
            api_base=args.api_base,
            api_key=args.api_key,
            model=args.model,
            funasr_vad_model=args.funasr_vad_model,
            funasr_punc_model=args.funasr_punc_model,
            funasr_device=args.funasr_device,
            doubaoime_credential_path=args.doubaoime_credential_path,
            doubaoime_device_id=args.doubaoime_device_id,
            doubaoime_token=args.doubaoime_token,
            doubaoime_enable_punctuation=not args.doubaoime_disable_punctuation,
            save_video=args.save_video,
            save_cover=args.save_cover,
            save_images=args.save_images,
            save_transcript=not args.skip_transcript,
        )
        print(json.dumps(extract_transcript(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
