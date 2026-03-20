# media-tool

一个面向短视频场景的解析与转写工具，提供 Web UI、HTTP API、CLI 和 MCP Server 四种使用方式。

`media-tool` 当前支持：

- 解析短视频分享文案或链接
- 获取视频、音频、封面和图集资源
- 通过异步任务执行 ASR 转写并轮询结果
- 使用 OpenAI 兼容大模型对转写文案做轻量校正
- 登录鉴权、主题切换、配置中心和可视化控制台
- Docker Compose 部署与 Windows 本地开发

## 功能特性

- 支持多平台短视频解析，当前核心场景已覆盖抖音，仓库中保留了其他平台下载器实现。
- Web 控制台支持登录后解析、异步转写、轮询进度、查看日志、预览资源和按需下载。
- 转写任务为“异步提交 + 轮询结果”结构，避免长请求直接阻塞前端。
- 转写过程中优先使用 `audio_url`，没有音频地址时自动回退为 `video_url`。
- 转写完成后默认清理临时下载文件，减少磁盘占用。
- 支持配置 OpenAI 兼容模型地址、密钥和模型名，对 ASR 结果进行错别字与语义连贯性校正。
- 支持 Docker Compose 一键部署，也支持 Windows 本地直接运行。

## 项目结构

```text
media-tool/
├─ media_tool_core/
│  ├─ api/                  # FastAPI 路由
│  ├─ configs/              # 环境变量、日志、常量
│  ├─ downloaders/          # 各平台解析下载器
│  ├─ services/             # 媒体解析、任务、鉴权、转写、LLM 校正
│  ├─ utils/                # ffmpeg、签名与通用工具
│  └─ schemas.py            # Pydantic 请求模型
├─ web/                     # Web UI 静态页面
├─ app.py                   # FastAPI 入口
├─ cli.py                   # 命令行入口
├─ mcp_server.py            # MCP Server 入口
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ .env.example
└─ README.md
```

运行期文件默认写入：

- `runtime\storage`
- `runtime\logs`
- `whisper-cache`

这些目录已加入忽略规则，不应提交到仓库。

## 技术栈

- Python 3.11+
- FastAPI
- requests
- yt-dlp
- Whisper ASR Web Service
- OpenAI 兼容 LLM 接口
- 原生 HTML / CSS / JavaScript

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd media-tool
```

### 2. 创建环境变量文件

Windows PowerShell：

```powershell
Copy-Item ".env.example" ".env"
```

macOS / Linux：

```bash
cp .env.example .env
```

### 3. 按需修改 `.env`

最少建议先修改以下字段：

- `MEDIA_TOOL_AUTH_USERNAME`
- `MEDIA_TOOL_AUTH_PASSWORD`
- `MEDIA_TOOL_TRANSCRIPTION_BASE_URL`
- `MEDIA_TOOL_LLM_API_BASE`
- `MEDIA_TOOL_LLM_API_KEY`
- `MEDIA_TOOL_LLM_MODEL`

## Docker Compose 部署

### 前置条件

- Docker Engine 或 Docker Desktop
- Docker Compose v2

### 启动

```powershell
docker compose up -d --build
```

默认会启动两个服务：

- `media-tool`：Web UI + HTTP API
- `whisper-asr`：Whisper ASR 服务

### 默认端口

- `8000 -> media-tool:8051`
- `9000 -> whisper-asr:9000`

### 查看状态

```powershell
docker compose ps
docker compose logs -f media-tool
docker compose logs -f whisper-asr
```

### 访问地址

- Web UI：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/api/health`

### 持久化说明

Compose 默认挂载以下目录：

- `.\media_tool_storage -> /app/runtime/storage`
- `.\media_tool_logs -> /app/runtime/logs`
- `.\whisper-cache -> /data/whisper`

其中 `whisper-cache` 用于缓存 Whisper 模型，避免容器重启后重复下载。

## Windows 本地开发

### 环境要求

- Python 3.11 或 3.12
- FFmpeg
- 可选：本地或远程 Whisper ASR 服务

### 1. 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. 安装依赖

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 配置 `.env`

本地调试建议至少设置：

```env
MEDIA_TOOL_RUNTIME_ROOT=D:\Code\Python\Ai\wechat\media-tool\runtime
MEDIA_TOOL_STORAGE_ROOT=D:\Code\Python\Ai\wechat\media-tool\runtime\storage
MEDIA_TOOL_LOG_ROOT=D:\Code\Python\Ai\wechat\media-tool\runtime\logs
MEDIA_TOOL_FFMPEG_PATH=D:\Env\FFmpeg\bin\ffmpeg.exe
MEDIA_TOOL_TRANSCRIPTION_BASE_URL=http://127.0.0.1:9000
MEDIA_TOOL_AUTH_USERNAME=admin
MEDIA_TOOL_AUTH_PASSWORD=admin123
```

### 4. 启动 Web 服务

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8051 --reload
```

打开：

```text
http://127.0.0.1:8051/
```

### 5. 启动本地 Whisper ASR

如果你使用容器方式单独启动 Whisper ASR，可执行：

```powershell
docker run -d --name whisper-asr `
  -p 9000:9000 `
  -e ASR_MODEL=small `
  -e ASR_ENGINE=faster_whisper `
  -e ASR_DEVICE=cpu `
  -e ASR_MODEL_PATH=/data/whisper `
  -v ${PWD}\whisper-cache:/data/whisper `
  onerahmet/openai-whisper-asr-webservice:latest
```

## Web UI 使用说明

### 登录页

- 首次进入需要登录。
- 登录页会跟随当前保存的明亮/暗黑主题。
- 登录账号密码由 `.env` 控制，也可以在配置中心修改密码。

### 控制台

主界面标题为“短视频解析转写控制台”，主要区域包括：

- 服务状态
- 主题模式切换
- 配置中心
- 媒体解析与异步转写表单
- 媒体信息
- 媒体预览与单项下载
- 执行反馈
- 转写结果

### 配置中心

配置中心使用模态框管理以下内容：

- Whisper ASR 地址与参数
- 是否保存 transcript
- 是否启用逐词时间戳
- 是否启用静音过滤
- LLM 接口地址、密钥、模型名和超时
- 修改密码
- 退出登录

### 异步任务流程

1. 输入分享文案或链接
2. 点击“解析链接”获取媒体信息
3. 点击“创建转写任务”
4. 前端轮询 `/api/jobs/{job_id}`
5. 实时显示任务进度、进度标签和日志
6. 任务完成后展示转写结果与 LLM 校正结果

## HTTP API

基础地址：

```text
http://127.0.0.1:8000
```

所有受保护接口都需要先登录并携带会话 Cookie。

### `GET /api/health`

健康检查。

响应示例：

```json
{
  "success": true,
  "message": "ok"
}
```

### `POST /api/auth/login`

登录。

请求体：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

### `POST /api/auth/logout`

退出登录。

### `GET /api/auth/me`

获取当前登录用户。

### `POST /api/auth/change-password`

修改密码。

请求体：

```json
{
  "current_password": "admin123",
  "new_password": "new-password",
  "confirm_password": "new-password"
}
```

### `POST /api/parse`

解析媒体信息。

请求体：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467"
}
```

响应示例：

```json
{
  "success": true,
  "data": {
    "video_id": "7396822576074460467",
    "platform": "抖音",
    "title": "示例标题",
    "source_url": "https://www.douyin.com/video/7396822576074460467",
    "redirect_url": "https://www.iesdouyin.com/share/video/7396822576074460467",
    "real_url": "https://www.iesdouyin.com/share/video/7396822576074460467",
    "video_url": "https://...",
    "audio_url": "https://...",
    "cover_url": "https://...",
    "author": {
      "nickname": "示例作者",
      "author_id": "123456",
      "avatar": "https://..."
    },
    "image_list": [],
    "is_image_post": false
  }
}
```

### `GET /api/asset`

按需预览或下载单项资源。

查询参数：

- `text`：分享文案或链接
- `kind`：`video` / `audio` / `cover` / `image`
- `index`：图集索引，仅 `kind=image` 时使用
- `disposition`：`inline` 或 `attachment`

示例：

```text
/api/asset?text=https%3A%2F%2Fwww.douyin.com%2Fvideo%2F7396822576074460467&kind=video&disposition=inline
```

### `POST /api/extract`

创建异步转写任务。

请求体示例：

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
  "llm_api_base": "https://api.openai.com/v1",
  "llm_api_key": "sk-xxx",
  "llm_model": "gpt-5.4",
  "llm_timeout": 90,
  "save_transcript": true,
  "save_video": false,
  "save_cover": false,
  "save_images": false
}
```

响应示例：

```json
{
  "success": true,
  "data": {
    "job_id": "2d0d6f8d7a9f4e07a68b95da8c2f1f6b",
    "status": "queued",
    "created_at": "2026-03-21T02:10:00Z",
    "updated_at": "2026-03-21T02:10:00Z",
    "progress_percent": 0,
    "progress_label": "任务已创建",
    "logs": [
      "[10:10:00] 任务已创建，等待执行。"
    ],
    "result": null,
    "error": null
  }
}
```

### `GET /api/jobs/{job_id}`

轮询异步任务状态。

响应示例：

```json
{
  "success": true,
  "data": {
    "job_id": "2d0d6f8d7a9f4e07a68b95da8c2f1f6b",
    "status": "running",
    "created_at": "2026-03-21T02:10:00Z",
    "updated_at": "2026-03-21T02:10:12Z",
    "progress_percent": 56,
    "progress_label": "ASR 正在识别音频",
    "logs": [
      "[10:10:00] 任务已创建，等待执行。",
      "[10:10:01] 开始执行转写任务。",
      "[10:10:03] 正在解析媒体链接。",
      "[10:10:08] 源文件下载完成，开始提交 ASR。"
    ],
    "result": null,
    "error": null
  }
}
```

## CLI

### 解析媒体信息

```powershell
python cli.py parse -t "https://www.douyin.com/video/7396822576074460467"
```

### 下载资源

```powershell
python cli.py download -t "https://www.douyin.com/video/7396822576074460467"
```

### 本地直接转写

```powershell
python cli.py extract `
  -t "https://www.douyin.com/video/7396822576074460467" `
  --transcription-base-url http://127.0.0.1:9000 `
  --transcription-language zh `
  --llm-api-base https://api.openai.com/v1 `
  --llm-api-key sk-xxx `
  --llm-model gpt-5.4
```

## MCP Server

启动：

```powershell
python mcp_server.py
```

当前暴露的工具：

- `parse_media_info`
- `download_media_assets`
- `extract_media_copy`

## 环境变量说明

完整示例见 [`.env.example`](D:\Code\Python\Ai\wechat\media-tool\.env.example)。

核心变量如下：

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_RUNTIME_ROOT` | 项目根目录下的 `runtime` | 运行时根目录 |
| `MEDIA_TOOL_STORAGE_ROOT` | `runtime/storage` | 导出文件、临时文件、认证配置目录 |
| `MEDIA_TOOL_LOG_ROOT` | `runtime/logs` | 日志目录 |
| `MEDIA_TOOL_FFMPEG_PATH` | 空 | 本地运行时 ffmpeg 完整路径 |
| `MEDIA_TOOL_REQUEST_TIMEOUT` | `30` | 常规请求超时 |
| `MEDIA_TOOL_DOWNLOAD_RETRY_ATTEMPTS` | `3` | 媒体下载重试次数 |
| `MEDIA_TOOL_JOB_WORKERS` | `2` | 异步任务线程数 |
| `MEDIA_TOOL_JOB_MAX_LOGS` | `120` | 单任务日志保留条数 |
| `MEDIA_TOOL_AUTH_USERNAME` | `admin` | 登录账号 |
| `MEDIA_TOOL_AUTH_PASSWORD` | `admin123` | 登录密码 |
| `MEDIA_TOOL_AUTH_COOKIE_SECURE` | `false` | HTTPS 下建议改为 `true` |
| `MEDIA_TOOL_AUTH_SESSION_TTL` | `604800` | 登录会话时长 |
| `MEDIA_TOOL_TRANSCRIPTION_BASE_URL` | `http://whisper-asr:9000` | Whisper ASR 地址 |
| `MEDIA_TOOL_TRANSCRIPTION_TASK` | `transcribe` | 转写任务类型 |
| `MEDIA_TOOL_TRANSCRIPTION_LANGUAGE` | `zh` | 默认语言 |
| `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT` | `300` | ASR 超时 |
| `MEDIA_TOOL_TRANSCRIPTION_ENCODE` | `true` | 是否预先重编码 |
| `MEDIA_TOOL_TRANSCRIPTION_WORD_TIMESTAMPS` | `false` | 是否返回逐词时间戳 |
| `MEDIA_TOOL_TRANSCRIPTION_VAD_FILTER` | `false` | 是否启用静音过滤 |
| `MEDIA_TOOL_LLM_API_BASE` | `https://api.openai.com/v1` | LLM 接口地址 |
| `MEDIA_TOOL_LLM_API_KEY` | 空 | LLM 密钥 |
| `MEDIA_TOOL_LLM_MODEL` | `gpt-5.4` | LLM 模型名 |
| `MEDIA_TOOL_LLM_TIMEOUT` | `90` | LLM 超时 |
| `MEDIA_TOOL_ASR_ENGINE` | `faster_whisper` | Whisper 引擎 |
| `MEDIA_TOOL_ASR_MODEL` | `small` | Whisper 模型 |
| `MEDIA_TOOL_ASR_DEVICE` | `cpu` | Whisper 运行设备 |

## 常见问题

### 1. 提示未检测到 ffmpeg

请确认：

- 已正确安装 FFmpeg
- `ffmpeg.exe` 已加入系统 `PATH`
- 或在 `.env` 中设置 `MEDIA_TOOL_FFMPEG_PATH=D:\Env\FFmpeg\bin\ffmpeg.exe`

### 2. `/api/extract` 很慢或超时

建议优先使用：

- 异步任务接口 `/api/extract`
- 前端轮询 `/api/jobs/{job_id}`
- 本地网络可直连的 Whisper ASR 地址
- 持久化 `whisper-cache`，避免重复下载模型

### 3. 转写结果不理想

可尝试：

- 更换更大的 Whisper 模型
- 开启 LLM 文案校正
- 增加 `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT`
- 使用更稳定的 ASR 部署环境

### 4. Windows 安装依赖时报 `lxml` 构建失败

优先建议：

- 使用 Python 3.11 或 3.12
- 升级 `pip`
- 尽量使用预编译 wheel
- 如果只是运行本项目，优先使用 Docker Compose，避免本地编译链问题

## 开发说明

- 仓库源码文件统一使用 UTF-8 编码。
- 运行期目录不要提交到 Git。
- 如需新增平台下载器，优先放在 `media_tool_core/downloaders/` 并通过 `downloader_factory.py` 接入。

## 许可证

当前仓库未附带 `LICENSE` 文件。如果你准备公开分发或接受外部贡献，建议尽快补充许可证声明。
