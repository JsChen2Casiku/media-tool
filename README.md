# media-tool

`media-tool` 是一个面向短视频场景的解析、下载与文案提取服务。

## 主要功能

- 解析多平台分享链接
- 下载视频文件
- 下载封面图片
- 下载图集内容
- 通过兼容 OpenAI 接口的转写模型提取文案
- 提供 HTTP API
- 提供 CLI
- 提供 MCP Server
- 支持 Docker Compose 部署

当前项目默认以 `Docker Compose` 方式部署。

## 项目结构

```text
media-tool/
|-- media_tool_core/          # 核心包
|-- app.py                    # FastAPI 入口
|-- cli.py                    # CLI 入口
|-- mcp_server.py             # MCP 入口
|-- Dockerfile                # 镜像定义
|-- docker-compose.yml        # Compose 配置
|-- .env.example              # 环境变量示例
|-- requirements.txt          # Python 依赖
`-- README.md
```

## 部署方式

### Docker Compose 部署

#### 前置要求

宿主机需要安装：

- Docker Desktop 或 Docker Engine
- Docker Compose v2

#### 1. 创建 `.env`

Windows PowerShell：

```powershell
Copy-Item 'D:\Code\Python\Ai\wechat\media-tool\.env.example' 'D:\Code\Python\Ai\wechat\media-tool\.env'
```

或者在项目目录下执行：

```powershell
copy .env.example .env
```

#### 2. 编辑 `.env`

至少需要配置：

```env
MEDIA_TOOL_API_KEY=sk-xxx
MEDIA_TOOL_API_BASE=https://api.openai.com/v1
MEDIA_TOOL_MODEL=gpt-4o-mini-transcribe
```

#### 3. 构建并启动

```powershell
docker compose up -d --build
```

#### 4. 查看状态

```powershell
docker compose ps
docker compose logs -f
```

#### 5. 健康检查

```powershell
curl http://localhost:8051/api/health
```

成功时返回：

```json
{"success": true, "message": "ok"}
```

## `.env` 字段说明

| 变量名 | 是否必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MEDIA_TOOL_API_BASE` | 否 | `https://api.openai.com/v1` | OpenAI 兼容接口基础地址 |
| `MEDIA_TOOL_API_KEY` | 是 | 空 | 转写接口密钥 |
| `MEDIA_TOOL_MODEL` | 否 | `gpt-4o-mini-transcribe` | 音频转写模型名 |
| `MEDIA_TOOL_REQUEST_TIMEOUT` | 否 | `30` | 普通 HTTP 请求超时时间，单位秒 |
| `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT` | 否 | `300` | 转写请求超时时间，单位秒 |
| `MAX_CACHE_SIZE_MB` | 否 | `15` | 缓存相关大小阈值，单位 MB |
| `MEDIA_TOOL_STORAGE_ROOT` | 否 | `/app/runtime/storage` | 容器内存储目录 |
| `MEDIA_TOOL_LOG_ROOT` | 否 | `/app/runtime/logs` | 容器内日志目录 |

推荐示例：

```env
MEDIA_TOOL_API_BASE=https://api.openai.com/v1
MEDIA_TOOL_API_KEY=sk-xxxxxxxxxxxxxxxx
MEDIA_TOOL_MODEL=gpt-4o-mini-transcribe
MEDIA_TOOL_REQUEST_TIMEOUT=30
MEDIA_TOOL_TRANSCRIPTION_TIMEOUT=300
MAX_CACHE_SIZE_MB=15
```

## 挂载与持久化

Compose 中定义了两个卷：

- `media_tool_storage` -> `/app/runtime/storage`
- `media_tool_logs` -> `/app/runtime/logs`

用途：

- `storage`：保存视频、封面、图集、转写文件、临时文件
- `logs`：保存应用日志

## HTTP API

基础地址：

```text
http://localhost:8051
```

### 1. 健康检查

`GET /api/health`

```powershell
curl http://localhost:8051/api/health
```

### 2. 解析链接

`POST /api/parse`

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467"
}
```

```powershell
curl -X POST http://localhost:8051/api/parse ^
  -H "Content-Type: application/json" ^
  -d "{"text":"https://www.douyin.com/video/7396822576074460467"}"
```

### 3. 下载资源

`POST /api/download`

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "output_dir": null,
  "save_video": true,
  "save_cover": true,
  "save_images": true
}
```

```powershell
curl -X POST http://localhost:8051/api/download ^
  -H "Content-Type: application/json" ^
  -d "{"text":"https://www.douyin.com/video/7396822576074460467","save_video":true,"save_cover":true,"save_images":true}"
```

### 4. 提取文案

`POST /api/extract`

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model": "gpt-4o-mini-transcribe",
  "save_transcript": true,
  "save_video": false,
  "save_cover": true,
  "save_images": false
}
```

```powershell
curl -X POST http://localhost:8051/api/extract ^
  -H "Content-Type: application/json" ^
  -d "{"text":"https://www.douyin.com/video/7396822576074460467","api_base":"https://api.openai.com/v1","api_key":"sk-xxx","model":"gpt-4o-mini-transcribe","save_transcript":true}"
```

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

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --api-base https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o-mini-transcribe
```

## MCP

启动：

```powershell
python mcp_server.py
```

可用工具：

- `parse_media_info`
- `download_media_assets`
- `extract_media_copy`

## 宿主机直接运行

如果不使用 Docker，可以直接在本机运行：

```powershell
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8051
```

此模式下仍然需要宿主机安装 `ffmpeg` 并加入 `PATH`。

## 故障排查

### `/api/extract` 返回 400

请检查：

- `MEDIA_TOOL_API_KEY` 已配置
- `MEDIA_TOOL_API_BASE` 可访问
- `MEDIA_TOOL_MODEL` 填写正确
- 如果不是 Docker 部署，宿主机已安装 `ffmpeg`

### `docker compose up` 失败

请检查：

- Docker Desktop 已启动
- `docker compose version` 可用
- 端口 `8051` 未被占用
