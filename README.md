# media-tool

`media-tool` 是一个面向短视频场景的统一工具，支持链接解析、媒体预览、按需下载、封面与图集获取，以及音频转写文案提取。

当前项目提供四种入口：

- Web UI
- HTTP API
- CLI
- MCP Server

同时支持三种转写后端：

- `openai`：对接兼容 `POST /audio/transcriptions` 的 API
- `funasr`：本地推理
- `doubaoime`：接入 `doubaoime-asr` 客户端能力

## 功能概览

- 多平台短视频链接解析
- 视频、音频、封面、图集预览
- 视频、音频、封面、图集单项下载
- 文案提取与保存
- Docker Compose 部署
- 浏览器可视化操作界面

## 项目结构

```text
media-tool/
|-- media_tool_core/          # 核心逻辑
|-- web/                      # Web UI 静态页面
|-- app.py                    # FastAPI 入口
|-- cli.py                    # CLI 入口
|-- mcp_server.py             # MCP Server 入口
|-- Dockerfile                # 容器镜像定义
|-- docker-compose.yml        # Compose 配置
|-- .env.example              # 环境变量示例
|-- requirements.txt          # Python 依赖
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
MEDIA_TOOL_TRANSCRIBER_BACKEND=openai
MEDIA_TOOL_API_BASE=https://api.openai.com/v1
MEDIA_TOOL_API_KEY=sk-xxxx
MEDIA_TOOL_MODEL=gpt-4o-mini-transcribe

MEDIA_TOOL_FUNASR_MODEL=paraformer-zh
MEDIA_TOOL_FUNASR_VAD_MODEL=fsmn-vad
MEDIA_TOOL_FUNASR_PUNC_MODEL=ct-punc
MEDIA_TOOL_FUNASR_DEVICE=auto

MEDIA_TOOL_DOUBAOIME_MODEL=doubaoime-asr
MEDIA_TOOL_DOUBAOIME_CREDENTIAL_PATH=/app/runtime/storage/doubaoime/credentials.json
MEDIA_TOOL_DOUBAOIME_DEVICE_ID=
MEDIA_TOOL_DOUBAOIME_TOKEN=
MEDIA_TOOL_DOUBAOIME_ENABLE_PUNCTUATION=true
```

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

成功时返回：

```json
{"success": true, "message": "ok"}
```

## 环境变量说明

### 通用配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_TRANSCRIBER_BACKEND` | `openai` | 默认转写后端，可选 `openai`、`funasr`、`doubaoime` |
| `MEDIA_TOOL_REQUEST_TIMEOUT` | `30` | 普通 HTTP 请求超时，单位秒 |
| `MEDIA_TOOL_TRANSCRIPTION_TIMEOUT` | `300` | 转写请求超时，单位秒 |
| `MEDIA_TOOL_STORAGE_ROOT` | `/app/runtime/storage` | 容器内存储目录 |
| `MEDIA_TOOL_LOG_ROOT` | `/app/runtime/logs` | 容器内日志目录 |
| `MAX_CACHE_SIZE_MB` | `15` | 缓存上限，单位 MB |

### OpenAI 兼容转写配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_API_BASE` | `https://api.openai.com/v1` | OpenAI 兼容接口基础地址 |
| `MEDIA_TOOL_API_KEY` | 空 | 接口密钥 |
| `MEDIA_TOOL_MODEL` | `gpt-4o-mini-transcribe` | 转写模型名 |

注意：

- 该后端要求上游实现 `POST /audio/transcriptions`
- 如果兼容网关没有实现这条接口，`/api/extract` 会返回 400 或 404

### FunASR 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_FUNASR_MODEL` | `paraformer-zh` | FunASR 主模型 |
| `MEDIA_TOOL_FUNASR_VAD_MODEL` | `fsmn-vad` | VAD 模型 |
| `MEDIA_TOOL_FUNASR_PUNC_MODEL` | `ct-punc` | 标点模型 |
| `MEDIA_TOOL_FUNASR_DEVICE` | `auto` | 运行设备，如 `cpu`、`cuda:0` |

注意：

- FunASR 在容器内本地运行
- 依赖 `torch`、`torchaudio`、`funasr`、`modelscope`
- 镜像体积会明显增加

### 豆包输入法 ASR 配置

本能力接入自 GitHub 仓库 `starccy/doubaoime-asr`。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEDIA_TOOL_DOUBAOIME_MODEL` | `doubaoime-asr` | 元数据中的后端标识 |
| `MEDIA_TOOL_DOUBAOIME_CREDENTIAL_PATH` | `/app/runtime/storage/doubaoime/credentials.json` | 凭据缓存文件路径 |
| `MEDIA_TOOL_DOUBAOIME_DEVICE_ID` | 空 | 可选，手动指定设备 ID |
| `MEDIA_TOOL_DOUBAOIME_TOKEN` | 空 | 可选，手动指定 Token |
| `MEDIA_TOOL_DOUBAOIME_ENABLE_PUNCTUATION` | `true` | 是否自动加标点 |

注意：

- 首次运行时，如果未提供 `device_id` 与 `token`，库可能自动注册设备并缓存凭据
- 容器中已安装 `libopus0`
- 该能力属于非官方接口方案，稳定性取决于上游协议是否变化

## Web UI

启动后直接访问：

```text
http://localhost:8000/
```

### 当前界面工作流

Web UI 已改为“解析 -> 预览 -> 提取”的操作流：

1. 在“任务参数”区域粘贴分享文案或链接
2. 选择转写后端：`openai`、`funasr` 或 `doubaoime`
3. 填写对应参数
4. 点击“解析链接”
5. 在“媒体预览与单项下载”区域直接查看并下载需要的资源
6. 如果需要文案，再点击“提取文案”

### Web UI 能做什么

- 粘贴短视频分享链接
- 切换三种转写后端
- 配置 API 地址、密钥、模型名
- 配置 FunASR 参数
- 配置豆包凭据路径、设备 ID、Token、自动标点
- 查看解析结果摘要
- 预览视频
- 预览音频
- 预览封面
- 预览图集
- 单独下载视频、音频、封面或图集图片
- 复制转写文案

### 当前 UI 交互说明

- 已取消独立“下载资源”主按钮
- 下载入口改为预览卡片里的单项下载按钮
- 解析摘要里不再展示作者信息
- 媒体预览和下载都通过同源 `/api/asset` 接口代理
- 转写使用的临时视频与音频文件在服务端完成后自动删除

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

### `POST /api/download`

该接口仍然保留，适合脚本或批处理使用：

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "save_video": true,
  "save_cover": true,
  "save_images": true
}
```

注意：

- Web UI 已不再直接使用这个接口
- 浏览器界面改为通过 `/api/asset` 做预览和单项下载

### `GET /api/asset`

用于媒体预览与单项下载。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `text` | 是 | 原始分享文案或链接 |
| `kind` | 是 | `video`、`audio`、`cover`、`image` |
| `index` | 否 | 图集索引，仅 `kind=image` 时使用，从 `0` 开始 |
| `disposition` | 否 | `inline` 或 `attachment` |

#### 预览视频

```text
GET /api/asset?text=https%3A%2F%2Fwww.douyin.com%2Fvideo%2F7396822576074460467&kind=video&disposition=inline
```

#### 下载封面

```text
GET /api/asset?text=https%3A%2F%2Fwww.douyin.com%2Fvideo%2F7396822576074460467&kind=cover&disposition=attachment
```

#### 下载第 1 张图集图片

```text
GET /api/asset?text=https%3A%2F%2Fexample.com%2Fpost&kind=image&index=0&disposition=attachment
```

### `POST /api/extract`

#### OpenAI 兼容后端示例

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "backend": "openai",
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model": "gpt-4o-mini-transcribe",
  "save_transcript": true,
  "save_video": false,
  "save_cover": false,
  "save_images": false
}
```

#### FunASR 后端示例

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "backend": "funasr",
  "model": "paraformer-zh",
  "funasr_vad_model": "fsmn-vad",
  "funasr_punc_model": "ct-punc",
  "funasr_device": "cpu",
  "save_transcript": true,
  "save_video": false,
  "save_cover": false,
  "save_images": false
}
```

#### 豆包输入法 ASR 后端示例

```json
{
  "text": "https://www.douyin.com/video/7396822576074460467",
  "backend": "doubaoime",
  "doubaoime_credential_path": "/app/runtime/storage/doubaoime/credentials.json",
  "doubaoime_enable_punctuation": true,
  "save_transcript": true,
  "save_video": false,
  "save_cover": false,
  "save_images": false
}
```

说明：

- `transcription` 字段会返回当前后端及其关键元数据
- 转写过程中下载的视频和抽取的音频文件会放在临时目录
- 转写结束后这些临时文件会自动删除

## CLI

### 解析

```powershell
python cli.py parse -t "https://www.douyin.com/video/7396822576074460467"
```

### 下载

```powershell
python cli.py download -t "https://www.douyin.com/video/7396822576074460467"
```

### OpenAI 兼容后端提取

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --backend openai --api-base https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o-mini-transcribe
```

### FunASR 提取

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --backend funasr --model paraformer-zh --funasr-vad-model fsmn-vad --funasr-punc-model ct-punc --funasr-device cpu
```

### 豆包输入法 ASR 提取

```powershell
python cli.py extract -t "https://www.douyin.com/video/7396822576074460467" --backend doubaoime --doubaoime-credential-path ./credentials.json
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

如果不使用 Docker，也可以直接运行：

```powershell
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8051
```

额外要求：

- 本机需要安装 `ffmpeg`
- 如果启用 `doubaoime`，系统还需要可用的 `libopus` 运行库

## 常见问题

### 1. `/api/extract` 返回 404

如果你使用的是 `openai` 后端，这通常意味着你的上游服务没有实现：

```text
POST /audio/transcriptions
```

这种情况下请改用：

- 真正支持音频转写的 OpenAI 兼容服务
- `funasr`
- `doubaoime`

### 2. 提示找不到 `ffmpeg`

非 Docker 部署时，需要自行安装 `ffmpeg` 并加入 `PATH`。

Docker Compose 镜像内已内置 `ffmpeg`。

### 3. 豆包输入法 ASR 首次运行失败

建议先确认：

- 容器已重新执行 `docker compose build --no-cache`
- `MEDIA_TOOL_DOUBAOIME_CREDENTIAL_PATH` 所在目录可写
- 网络能够访问该后端所需的远端服务

### 4. 为什么 Web UI 没有“下载资源”大按钮了

这是当前设计调整后的结果。

现在的界面逻辑是：

- 先解析
- 再直接预览
- 在每个媒体卡片中按需单独下载

这样可以避免整包下载，操作更细，也更适合预览后再决定是否保存。

### 5. 转写结束后文件会不会堆积

不会。

转写时用来抽音频的原始视频和中间音频文件都存放在临时目录，转写完成后会自动删除。只有你显式要求保存的 `transcript.md`、视频、封面或图集文件才会保留。
