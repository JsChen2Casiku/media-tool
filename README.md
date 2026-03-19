# media-tool

`media-tool` 是一个面向短视频场景的统一工具，支持链接解析、媒体预览、按需下载、文案提取，并提供 Web UI、HTTP API、CLI、MCP Server 四种入口。

当前项目的转写能力已经统一重构为 `OpenTypeless` 模型链，不再保留旧的 `openai`、`funasr`、独立旧豆包参数配置。

支持的转写模型：

- `doubao-asr`
- `doubao-asr-official`
- `doubao-asr-official-standard`
- `doubao-asr-official-flash`

## 功能概览

- 多平台短视频链接解析
- 视频、音频、封面、图集预览
- 视频、音频、封面、图集单项下载
- 使用 OpenTypeless 进行文案提取
- Docker Compose 部署
- 浏览器可视化操作界面

## 项目结构

```text
media-tool/
|-- media_tool_core/          # 核心逻辑
|-- doubaoime_asr/            # OpenTypeless IME 模式依赖的本地最小实现
|-- web/                      # Web UI 静态页面
|-- app.py                    # FastAPI 入口
|-- cli.py                    # CLI 入口
|-- mcp_server.py             # MCP Server 入口
|-- Dockerfile
|-- docker-compose.yml
|-- .env.example
|-- requirements.txt
`-- README.md
```

## Docker Compose 部署

### 前置要求

- Docker Engine 或 Docker Desktop
- Docker Compose v2

### 1. 创建 `.env`

PowerShell：

```powershell
Copy-Item "D:\Code\Python\Ai\wechat\media-tool\.env.example" "D:\Code\Python\Ai\wechat\media-tool\.env"
```

或在项目目录执行：

```powershell
copy .env.example .env
```

### 2. 配置 `.env`

示例：

```env
MEDIA_TOOL_PIP_INDEX_URL=https://pypi.org/simple
MEDIA_TOOL_PIP_EXTRA_INDEX_URL=

MEDIA_TOOL_OPENTYPELESS_MODEL=doubao-asr
MEDIA_TOOL_OPENTYPELESS_CREDENTIAL_PATH=/app/runtime/storage/opentypeless/credentials.json
MEDIA_TOOL_OPENTYPELESS_DEVICE_ID=
MEDIA_TOOL_OPENTYPELESS_TOKEN=
MEDIA_TOOL_OPENTYPELESS_DEFAULT_BACKEND=ime
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODE=flash
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY=
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY=
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_SUBMIT_ENDPOINT=https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_QUERY_ENDPOINT=https://openspeech.bytedance.com/api/v3/auc/bigmodel/query
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_ENDPOINT=https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_RESOURCE_ID=volc.seedasr.auc
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_RESOURCE_ID=volc.bigasr.auc_turbo
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODEL_NAME=bigmodel
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_UID=opentypeless
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_TIMEOUT_SEC=120
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_INTERVAL_SEC=1.0
MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_TIMEOUT_SEC=300

MEDIA_TOOL_REQUEST_TIMEOUT=30
MAX_CACHE_SIZE_MB=15
```

说明：

- `doubao-asr` 为 IME 模式，通常依赖本地凭据缓存
- `doubao-asr-official*` 为官方文件识别模式，需要填写 `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY` 与 `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY`
- 如果服务器访问 PyPI 不稳定，可以把 `MEDIA_TOOL_PIP_INDEX_URL` 改成可用镜像

### 3. 构建并启动

```powershell
docker compose up -d --build
```

### 4. 查看状态

```powershell
docker compose ps
docker compose logs -f media-tool
```

### 5. 健康检查

```powershell
curl http://localhost:8000/api/health
```

返回：

```json
{"success": true, "message": "ok"}
```

## 环境变量说明

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_PIP_INDEX_URL` | `https://pypi.org/simple` | Docker 构建时使用的主 PyPI 源 |
| `MEDIA_TOOL_PIP_EXTRA_INDEX_URL` | 空 | 可选的额外 Python 包源 |
| `MEDIA_TOOL_OPENTYPELESS_MODEL` | `doubao-asr` | 默认转写模型 |
| `MEDIA_TOOL_OPENTYPELESS_CREDENTIAL_PATH` | `/app/runtime/storage/opentypeless/credentials.json` | IME 模式凭据缓存文件路径 |
| `MEDIA_TOOL_OPENTYPELESS_DEVICE_ID` | 空 | IME 模式设备 ID，可选 |
| `MEDIA_TOOL_OPENTYPELESS_TOKEN` | 空 | IME 模式 Token，可选 |
| `MEDIA_TOOL_OPENTYPELESS_DEFAULT_BACKEND` | `ime` | 默认后端，支持 `ime`、`official` |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODE` | `flash` | 官方模式，支持 `flash`、`standard` |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY` | 空 | 官方文件识别 App Key |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY` | 空 | 官方文件识别 Access Key |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_SUBMIT_ENDPOINT` | 官方默认 submit 地址 | 官方标准版提交地址 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_QUERY_ENDPOINT` | 官方默认 query 地址 | 官方标准版查询地址 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_ENDPOINT` | 官方默认 flash 地址 | 官方极速版识别地址 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_STANDARD_RESOURCE_ID` | `volc.seedasr.auc` | 官方标准版资源 ID |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_FLASH_RESOURCE_ID` | `volc.bigasr.auc_turbo` | 官方极速版资源 ID |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODEL_NAME` | `bigmodel` | 官方请求模型名 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_UID` | `opentypeless` | 官方请求 UID |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_TIMEOUT_SEC` | `120` | 官方接口请求超时，单位秒 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_INTERVAL_SEC` | `1.0` | 官方标准版轮询间隔，单位秒 |
| `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_QUERY_TIMEOUT_SEC` | `300` | 官方标准版总轮询超时，单位秒 |
| `MEDIA_TOOL_STORAGE_ROOT` | `/app/runtime/storage` | 容器内存储目录 |
| `MEDIA_TOOL_LOG_ROOT` | `/app/runtime/logs` | 容器内日志目录 |
| `MEDIA_TOOL_REQUEST_TIMEOUT` | `30` | 普通 HTTP 请求超时，单位秒 |
| `MAX_CACHE_SIZE_MB` | `15` | 缓存上限，单位 MB |

## OpenTypeless 模型说明

### 1. `doubao-asr`

- IME 模式
- 依赖本地凭据缓存
- 适合不使用官方文件识别 Key 的场景

### 2. `doubao-asr-official`

- 官方文件识别模式
- 具体走 `flash` 还是 `standard` 取决于 `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_MODE`

### 3. `doubao-asr-official-standard`

- 强制官方标准版
- 采用提交任务加轮询查询的方式

### 4. `doubao-asr-official-flash`

- 强制官方极速版
- 单次请求返回，延迟更低

## Web UI

启动后访问：

```text
http://localhost:8000/
```

### 当前界面工作流

1. 粘贴分享文案或链接
2. 选择 OpenTypeless 模型
3. 根据模型填写对应参数
4. 点击“解析链接”查看媒体结果
5. 在预览区域按需下载视频、音频、封面或图集
6. 点击“提取文案”获取转写结果

### 当前界面可配置项

- OpenTypeless 模型
- IME 凭据文件
- IME 设备 ID
- IME Token
- 官方默认模式
- 官方 App Key
- 官方 Access Key
- 官方 UID

### 当前界面特性

- 不再提供旧的后端切换
- 不再提供独立“下载资源”大按钮
- 下载入口位于各资源卡片内部
- 解析摘要中不展示作者
- 转写完成后自动删除临时视频和中间音频文件

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

用于媒体预览与单项下载。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `text` | 是 | 原始分享文案或链接 |
| `kind` | 是 | `video`、`audio`、`cover`、`image` |
| `index` | 否 | 图集索引，仅 `kind=image` 时使用 |
| `disposition` | 否 | `inline` 或 `attachment` |

### `POST /api/extract`

IME 模式示例：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "model": "doubao-asr",
  "opentypeless_credential_path": "/app/runtime/storage/opentypeless/credentials.json",
  "save_transcript": true
}
```

官方极速版示例：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "model": "doubao-asr-official-flash",
  "opentypeless_official_app_key": "your-app-key",
  "opentypeless_official_access_key": "your-access-key",
  "opentypeless_official_uid": "opentypeless",
  "save_transcript": true
}
```

返回中的 `transcription` 字段会包含：

- `backend`
- `model`
- `mode`
- `credential_path`
- `device_id`
- `official_uid`

## CLI

### 解析

```powershell
python cli.py parse -t "https://www.douyin.com/video/7396822576074460467"
```

### 下载

```powershell
python cli.py download -t "https://www.douyin.com/video/7396822576074460467"
```

### IME 模式提取

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --model doubao-asr --credential-path ./credentials.json
```

### 官方极速版提取

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --model doubao-asr-official-flash --official-app-key your-app-key --official-access-key your-access-key
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

## 本地直接运行

```powershell
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8051
```

额外要求：

- 本机需要安装 `ffmpeg`
- IME 模式需要系统可用的 `libopus` 运行库

## 常见问题

### 1. `docker compose build` 失败

建议先执行：

```powershell
docker compose build --no-cache --progress=plain
```

如果是 Python 包下载失败：

- 检查 `MEDIA_TOOL_PIP_INDEX_URL`
- 改为可用镜像后重试

### 2. 官方模式返回缺少配置

请确认已填写：

- `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_APP_KEY`
- `MEDIA_TOOL_OPENTYPELESS_OFFICIAL_ACCESS_KEY`

### 3. IME 模式转写失败

建议确认：

- `MEDIA_TOOL_OPENTYPELESS_CREDENTIAL_PATH` 所在目录可写
- 如凭据已失效，可删除旧凭据文件后重试
- 容器已重新执行 `docker compose build --no-cache`

### 4. 提示找不到 `ffmpeg`

非 Docker 部署时，需要自行安装 `ffmpeg` 并加入 `PATH`。

Docker Compose 镜像内已内置 `ffmpeg`。

### 5. 转写结束后文件会不会堆积

不会。

转写时使用的原始视频和中间音频只会放在临时目录，完成后自动清理。只有显式要求保存的 `transcript.md`、视频、封面或图集才会保留。
