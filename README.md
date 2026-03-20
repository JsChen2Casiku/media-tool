# media-tool

`media-tool` 是一个面向短视频场景的统一工具，支持：

- 多平台短视频链接解析
- 视频、音频、封面、图集预览
- 按资源单独下载
- 基于免费自托管 Whisper ASR 的异步文案提取
- Web UI、HTTP API、CLI、MCP Server
- Docker Compose 部署

当前项目的转写能力已经统一切换到免费开源、自托管的 Whisper ASR Web Service，并采用“异步任务 + 前端轮询”的方式，避免长请求超时。

## 功能概览

- 解析短视频分享文案或链接
- 返回视频地址、音频地址、封面地址、图集地址
- 浏览器内直接预览视频、音频、封面和图集
- 每个资源单独下载，不再保留总下载按钮
- 转写时优先使用 `audio_url`，没有音频地址时回退到 `video_url`
- 创建异步转写任务，前端轮询结果
- 转写结束后自动删除临时下载文件

## 项目结构

```text
media-tool/
|-- media_tool_core/          # 核心逻辑
|-- web/                      # Web UI
|-- app.py                    # FastAPI 入口
|-- cli.py                    # CLI 入口
|-- mcp_server.py             # MCP Server 入口
|-- Dockerfile
|-- docker-compose.yml
|-- .env.example
|-- requirements.txt
`-- README.md
```

## 免费方案说明

项目当前推荐的转写方案是自托管 `whisper-asr-webservice`。

- 开源仓库：`ahmetoner/whisper-asr-webservice`
- 运行方式：本地或 Docker 自行部署
- 计费方式：项目本身免费，不需要购买第三方语音 API
- 成本来源：只会消耗你自己的机器 CPU / GPU / 内存资源

这和 `Deepgram`、`AssemblyAI` 这类按量计费的商业 API 不同。

## Docker Compose 部署

### 前置要求

- Docker Engine 或 Docker Desktop
- Docker Compose v2

### 1. 创建 `.env`

PowerShell：

```powershell
Copy-Item "D:\Code\Python\Ai\wechat\media-tool\.env.example" "D:\Code\Python\Ai\wechat\media-tool\.env"
```

或者在项目目录执行：

```powershell
copy .env.example .env
```

### 2. 配置 `.env`

示例：

```env
MEDIA_TOOL_FFMPEG_PATH=
MEDIA_TOOL_REQUEST_TIMEOUT=30
MAX_CACHE_SIZE_MB=15

MEDIA_TOOL_TRANSCRIPTION_BASE_URL=http://whisper-asr:9000
MEDIA_TOOL_TRANSCRIPTION_TASK=transcribe
MEDIA_TOOL_TRANSCRIPTION_LANGUAGE=zh
MEDIA_TOOL_TRANSCRIPTION_TIMEOUT=300
MEDIA_TOOL_TRANSCRIPTION_ENCODE=true
MEDIA_TOOL_TRANSCRIPTION_WORD_TIMESTAMPS=false
MEDIA_TOOL_TRANSCRIPTION_VAD_FILTER=false

MEDIA_TOOL_ASR_ENGINE=faster_whisper
MEDIA_TOOL_ASR_MODEL=small
MEDIA_TOOL_ASR_DEVICE=cpu
```

### 3. 启动服务

```powershell
docker compose up -d --build
```

### 4. 查看状态

```powershell
docker compose ps
docker compose logs -f media-tool
docker compose logs -f whisper-asr
```

第一次启动 `whisper-asr` 时，镜像可能会下载模型，耗时取决于网络与模型大小。

### 5. 健康检查

```powershell
curl http://localhost:8000/api/health
```

返回：

```json
{"success": true, "message": "ok"}
```

## `.env` 字段说明

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_FFMPEG_PATH` | 空 | 本地运行时可显式指定 `ffmpeg.exe` 路径 |
| `MEDIA_TOOL_REQUEST_TIMEOUT` | `30` | 常规 HTTP 请求超时，单位秒 |
| `MAX_CACHE_SIZE_MB` | `15` | 缓存大小上限 |
| `MEDIA_TOOL_TRANSCRIPTION_BASE_URL` | `http://whisper-asr:9000` | Whisper ASR 服务地址 |
| `MEDIA_TOOL_TRANSCRIPTION_TASK` | `transcribe` | 转写任务，支持 `transcribe` 或 `translate` |
| `MEDIA_TOOL_TRANSCRIPTION_LANGUAGE` | `zh` | 默认语言代码，留空时自动检测 |
| `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT` | `300` | 转写超时，单位秒 |
| `MEDIA_TOOL_TRANSCRIPTION_ENCODE` | `true` | 是否让 ASR 服务先重编码 |
| `MEDIA_TOOL_TRANSCRIPTION_WORD_TIMESTAMPS` | `false` | 是否返回逐词时间戳 |
| `MEDIA_TOOL_TRANSCRIPTION_VAD_FILTER` | `false` | 是否启用静音过滤 |
| `MEDIA_TOOL_ASR_ENGINE` | `faster_whisper` | Whisper 服务引擎 |
| `MEDIA_TOOL_ASR_MODEL` | `small` | Whisper 模型大小 |
| `MEDIA_TOOL_ASR_DEVICE` | `cpu` | Whisper 运行设备，可设为 `cpu` 或 `cuda` |
| `MEDIA_TOOL_DOWNLOAD_RETRY_ATTEMPTS` | `3` | 下载媒体源文件时的自动重试次数 |
| `MEDIA_TOOL_JOB_WORKERS` | `2` | 后台异步转写线程数 |
| `MEDIA_TOOL_JOB_MAX_LOGS` | `120` | 单个任务保留的最大日志条数 |

## Web UI

启动后访问：

```text
http://localhost:8000/
```

### 当前界面能力

- 粘贴分享文案或链接
- 配置 Whisper ASR 服务地址、任务、语言和超时
- 选择是否启用重编码、逐词时间戳、静音过滤
- 点击“解析链接”查看精简后的媒体信息
- 点击“开始转写”创建异步任务，前端自动轮询结果
- 在预览区分别预览和下载视频、音频、封面、图集

### 界面说明

- 顶部已改成紧凑工具台，不再使用大面积说明区
- 右侧固定显示执行状态、任务日志和媒体信息
- 日志区域固定高度，超出后内部滚动
- 提供“复制日志”按钮，方便排查任务失败原因
- 视频预览位于左侧，音频和封面位于右侧上下排列
- 不再展示视频、音频、封面地址文本
- 文案提取完成后，服务端会自动删除临时下载文件

## HTTP API

基础地址：

```text
http://localhost:8000
```

### `GET /api/health`

```powershell
curl http://localhost:8000/api/health
```

### `POST /api/parse`

请求：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467"
}
```

### `GET /api/asset`

用于媒体预览和单项下载。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `text` | 是 | 原始分享文案或链接 |
| `kind` | 是 | `video`、`audio`、`cover`、`image` |
| `index` | 否 | 图集索引，仅 `kind=image` 时使用 |
| `disposition` | 否 | `inline` 或 `attachment` |

示例：

```text
/api/asset?text=https%3A%2F%2Fwww.douyin.com%2Fvideo%2F7396822576074460467&kind=video&disposition=inline
```

### `POST /api/extract`

用于创建异步转写任务。

请求：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "transcription_base_url": "http://whisper-asr:9000",
  "transcription_task": "transcribe",
  "transcription_language": "zh",
  "transcription_timeout": 300,
  "transcription_encode": true,
  "transcription_word_timestamps": false,
  "transcription_vad_filter": false,
  "save_transcript": true
}
```

返回示例：

```json
{
  "success": true,
  "data": {
    "job_id": "2d0d6f8d7a9f4e07a68b95da8c2f1f6b",
    "status": "queued",
    "created_at": "2026-03-20T13:22:00Z",
    "updated_at": "2026-03-20T13:22:00Z",
    "logs": [
      "[13:22:00] 任务已创建，等待执行。"
    ],
    "result": null,
    "error": null
  }
}
```

### `GET /api/jobs/{job_id}`

用于轮询异步转写任务状态。

返回示例：

```json
{
  "success": true,
  "data": {
    "job_id": "2d0d6f8d7a9f4e07a68b95da8c2f1f6b",
    "status": "succeeded",
    "created_at": "2026-03-20T13:22:00Z",
    "updated_at": "2026-03-20T13:23:12Z",
    "logs": [
      "[13:22:00] 任务已创建，等待执行。",
      "[13:22:01] 开始执行转写任务。",
      "[13:22:05] 源文件下载完成，开始提交 Whisper ASR。",
      "[13:23:12] 任务执行完成。"
    ],
    "result": {
      "media": {},
      "transcript": "这里是转写后的文案",
      "output_dir": "/app/runtime/storage/exports/demo",
      "saved_files": {
        "transcript": "/app/runtime/storage/exports/demo/transcript.md",
        "video": null,
        "cover": null,
        "images": []
      },
      "transcription": {
        "provider": "whisper-asr-webservice",
        "base_url": "http://whisper-asr:9000",
        "endpoint": "http://whisper-asr:9000/asr",
        "task": "transcribe",
        "language": "zh",
        "detected_language": "zh",
        "segment_count": 12,
        "cleanup": "转写完成后自动删除临时下载文件"
      }
    },
    "error": null
  }
}
```

任务状态说明：

- `queued`：已创建，等待执行
- `running`：后台执行中
- `succeeded`：任务完成
- `failed`：任务失败

任务完成后，`result.transcription` 字段会包含：

- `provider`
- `base_url`
- `endpoint`
- `task`
- `language`
- `detected_language`
- `segment_count`
- `cleanup`

## CLI

### 解析

```powershell
python cli.py parse -t "https://www.douyin.com/video/7396822576074460467"
```

### 下载

```powershell
python cli.py download -t "https://www.douyin.com/video/7396822576074460467"
```

### 提取文案

当前 CLI 仍然是同步等待模式，适合本地直接运行，不经过 Cloudflare。

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --transcription-base-url http://127.0.0.1:9000 --transcription-language zh
```

## MCP Server

启动：

```powershell
python mcp_server.py
```

可用工具：

- `parse_media_info`
- `download_media_assets`
- `extract_media_copy`

## Windows 本地开发与调试

### 1. 建议 Python 版本

建议使用 `Python 3.11` 或 `Python 3.12`。

不建议直接使用 `Python 3.14`，因为部分三方依赖在 Windows 上可能没有现成 wheel。

### 2. 创建虚拟环境

```powershell
cd D:\Code\Python\Ai\wechat\media-tool
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 配置 `.env`

本地运行示例：

```env
MEDIA_TOOL_FFMPEG_PATH=D:\Env\FFmpeg\bin\ffmpeg.exe
MEDIA_TOOL_TRANSCRIPTION_BASE_URL=http://127.0.0.1:9000
MEDIA_TOOL_TRANSCRIPTION_TASK=transcribe
MEDIA_TOOL_TRANSCRIPTION_LANGUAGE=zh
MEDIA_TOOL_TRANSCRIPTION_TIMEOUT=300
```

### 4. 启动本地服务

```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8051 --reload
```

浏览器访问：

```text
http://127.0.0.1:8051/
```

## Windows 本地启动 whisper-asr

建议直接使用 Docker Desktop。

### 基础启动

```powershell
docker run -d `
  --name whisper-asr `
  -p 9000:9000 `
  -e ASR_ENGINE=faster_whisper `
  -e ASR_MODEL=small `
  -e ASR_DEVICE=cpu `
  onerahmet/openai-whisper-asr-webservice:latest
```

### 带模型缓存目录启动

```powershell
New-Item -ItemType Directory -Force -Path D:\Code\Python\Ai\wechat\media-tool\whisper-cache | Out-Null

docker run -d `
  --name whisper-asr `
  -p 9000:9000 `
  -e ASR_ENGINE=faster_whisper `
  -e ASR_MODEL=small `
  -e ASR_DEVICE=cpu `
  -e ASR_MODEL_PATH=/data/whisper `
  -v D:\Code\Python\Ai\wechat\media-tool\whisper-cache:/data/whisper `
  onerahmet/openai-whisper-asr-webservice:latest
```

启动后访问：

```text
http://127.0.0.1:9000/docs
```

## ffmpeg 说明

当前版本中：

- 解析、预览、Whisper 转写本身不依赖 `ffmpeg`
- 某些平台的视频下载或音视频合并流程仍可能依赖 `ffmpeg`

如果本地运行时提示找不到 `ffmpeg`，请确认：

1. `ffmpeg.exe` 已安装
2. 已加入系统 `PATH`
3. 或者在 `.env` 中显式设置：

```env
MEDIA_TOOL_FFMPEG_PATH=D:\Env\FFmpeg\bin\ffmpeg.exe
```

## 常见问题

### 1. 提取文案时报 404

通常是 `MEDIA_TOOL_TRANSCRIPTION_BASE_URL` 配错了。

本地运行 `media-tool`：

```text
http://127.0.0.1:9000
```

Docker Compose 内部：

```text
http://whisper-asr:9000
```

### 2. 网页提取文案超时

如果页面走了 Nginx 或 Cloudflare，长请求很容易超时。

当前 Web UI 已经改成异步任务 + 轮询结果：

1. `POST /api/extract` 创建任务
2. `GET /api/jobs/{job_id}` 轮询状态

因此不再依赖一个长连接等待完整转写。

### 3. 长视频转写不完整

当前实现会优先下载 `audio_url` 再上传到 Whisper 服务，这比直接用视频抽音频更稳定。

如果仍然不完整，可以尝试：

- 把 `MEDIA_TOOL_ASR_MODEL` 从 `small` 提高到 `medium`
- 延长 `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT`
- 保持 `MEDIA_TOOL_TRANSCRIPTION_ENCODE=true`

### 4. Windows 安装依赖失败

如果你在 Windows 上遇到编译型依赖报错，优先确认：

- 使用的是 `Python 3.11` 或 `Python 3.12`
- 已先执行 `python -m pip install --upgrade pip setuptools wheel`

### 5. Docker 首次启动很慢

这是 Whisper 模型首次下载造成的，属于正常现象。
