import argparse
import json

from media_tool_core.configs.env_loader import load_project_env

load_project_env()

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

    extract_cmd = subparsers.add_parser("extract", help="通过 Whisper ASR 提取文案，并可选使用 LLM 校正")
    extract_cmd.add_argument("--text", "-t", required=True, help="分享文案或链接")
    extract_cmd.add_argument("--output-dir", "-o", help="输出目录")
    extract_cmd.add_argument("--transcription-base-url", help="Whisper ASR 服务地址")
    extract_cmd.add_argument("--transcription-task", choices=["transcribe", "translate"], help="转写任务")
    extract_cmd.add_argument("--transcription-language", help="语言代码，例如 zh、en")
    extract_cmd.add_argument("--transcription-timeout", type=int, help="转写超时时间，单位秒")
    extract_cmd.add_argument(
        "--transcription-encode",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否先由 Whisper 服务执行重编码",
    )
    extract_cmd.add_argument(
        "--transcription-word-timestamps",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否返回逐词时间戳",
    )
    extract_cmd.add_argument(
        "--transcription-vad-filter",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否启用静音过滤",
    )
    extract_cmd.add_argument("--llm-api-base", help="OpenAI 兼容 LLM 基础地址")
    extract_cmd.add_argument("--llm-api-key", help="OpenAI 兼容 LLM API Key")
    extract_cmd.add_argument("--llm-model", help="LLM 校正模型名称，默认 gpt-5.4")
    extract_cmd.add_argument("--llm-timeout", type=int, help="LLM 校正超时时间，单位秒")
    extract_cmd.add_argument("--save-video", action="store_true", help="转写完成后保留视频文件")
    extract_cmd.add_argument("--save-cover", action="store_true", help="转写完成后保留封面文件")
    extract_cmd.add_argument("--save-images", action="store_true", help="转写完成后保留图集文件")
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
            transcription_base_url=args.transcription_base_url,
            transcription_task=args.transcription_task,
            transcription_language=args.transcription_language,
            transcription_timeout=args.transcription_timeout,
            transcription_encode=args.transcription_encode,
            transcription_word_timestamps=args.transcription_word_timestamps,
            transcription_vad_filter=args.transcription_vad_filter,
            llm_api_base=args.llm_api_base,
            llm_api_key=args.llm_api_key,
            llm_model=args.llm_model,
            llm_timeout=args.llm_timeout,
            save_video=args.save_video,
            save_cover=args.save_cover,
            save_images=args.save_images,
            save_transcript=not args.skip_transcript,
        )
        print(json.dumps(extract_transcript(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
