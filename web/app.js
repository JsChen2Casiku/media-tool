const qs = (selector) => document.querySelector(selector);

const DEFAULTS = {
  model: "doubao-asr",
  credentialPath: "/app/runtime/storage/opentypeless/credentials.json",
  officialMode: "flash",
  officialUid: "opentypeless",
};

const state = {
  lastParse: null,
  lastTranscript: "",
  lastText: "",
};

const elements = {
  text: qs("#media-text"),
  apiModel: qs("#api-model"),
  credentialPath: qs("#credential-path"),
  deviceId: qs("#device-id"),
  token: qs("#token"),
  officialMode: qs("#official-mode"),
  officialAppKey: qs("#official-app-key"),
  officialAccessKey: qs("#official-access-key"),
  officialUid: qs("#official-uid"),
  saveTranscript: qs("#save-transcript"),
  parseAction: qs("#parse-action"),
  extractAction: qs("#extract-action"),
  fillDemo: qs("#fill-demo"),
  clearResults: qs("#clear-results"),
  copyTranscript: qs("#copy-transcript"),
  statusTitle: qs("#status-title"),
  statusMessage: qs("#status-message"),
  statusCard: qs("#status-card"),
  healthStatus: qs("#health-status"),
  healthHint: qs("#health-hint"),
  resultSummary: qs("#result-summary"),
  previewGrid: qs("#preview-grid"),
  transcriptOutput: qs("#transcript-output"),
  summaryTemplate: qs("#summary-item-template"),
  credentialPathWrap: qs("#credential-path-wrap"),
  deviceIdWrap: qs("#device-id-wrap"),
  tokenWrap: qs("#token-wrap"),
  officialModeWrap: qs("#official-mode-wrap"),
  officialAppKeyWrap: qs("#official-app-key-wrap"),
  officialAccessKeyWrap: qs("#official-access-key-wrap"),
  officialUidWrap: qs("#official-uid-wrap"),
};

function setStatus(kind, title, message) {
  elements.statusCard.className = `status-card ${kind}`;
  elements.statusTitle.textContent = title;
  elements.statusMessage.textContent = message;
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function saveConfig() {
  const payload = {
    apiModel: elements.apiModel.value,
    credentialPath: elements.credentialPath.value.trim(),
    deviceId: elements.deviceId.value.trim(),
    token: elements.token.value.trim(),
    officialMode: elements.officialMode.value,
    officialAppKey: elements.officialAppKey.value.trim(),
    officialAccessKey: elements.officialAccessKey.value.trim(),
    officialUid: elements.officialUid.value.trim(),
  };
  localStorage.setItem("media-tool-config", JSON.stringify(payload));
}

function restoreConfig() {
  const raw = localStorage.getItem("media-tool-config");
  const parsed = raw ? safeJsonParse(raw) : {};

  elements.apiModel.value = parsed.apiModel || DEFAULTS.model;
  elements.credentialPath.value = parsed.credentialPath || DEFAULTS.credentialPath;
  elements.deviceId.value = parsed.deviceId || "";
  elements.token.value = parsed.token || "";
  elements.officialMode.value = parsed.officialMode || DEFAULTS.officialMode;
  elements.officialAppKey.value = parsed.officialAppKey || "";
  elements.officialAccessKey.value = parsed.officialAccessKey || "";
  elements.officialUid.value = parsed.officialUid || DEFAULTS.officialUid;

  syncModelFields(false);
}

function toggleElement(element, visible) {
  if (!element) {
    return;
  }
  element.hidden = !visible;
}

function isOfficialModel(model) {
  return model.startsWith("doubao-asr-official");
}

function syncModelFields(shouldSave = true) {
  const model = elements.apiModel.value.trim();
  const official = isOfficialModel(model);
  const genericOfficial = model === "doubao-asr-official";
  const ime = model === "doubao-asr";

  toggleElement(elements.credentialPathWrap, ime);
  toggleElement(elements.deviceIdWrap, ime);
  toggleElement(elements.tokenWrap, ime);

  toggleElement(elements.officialModeWrap, genericOfficial);
  toggleElement(elements.officialAppKeyWrap, official);
  toggleElement(elements.officialAccessKeyWrap, official);
  toggleElement(elements.officialUidWrap, official);

  if (ime && !elements.credentialPath.value.trim()) {
    elements.credentialPath.value = DEFAULTS.credentialPath;
  }
  if (official && !elements.officialUid.value.trim()) {
    elements.officialUid.value = DEFAULTS.officialUid;
  }

  if (shouldSave) {
    saveConfig();
  }
}

function getCommonPayload() {
  saveConfig();
  return {
    text: elements.text.value.trim(),
    model: elements.apiModel.value.trim(),
    opentypeless_credential_path: elements.credentialPath.value.trim(),
    opentypeless_device_id: elements.deviceId.value.trim(),
    opentypeless_token: elements.token.value.trim(),
    opentypeless_official_mode: elements.officialMode.value,
    opentypeless_official_app_key: elements.officialAppKey.value.trim(),
    opentypeless_official_access_key: elements.officialAccessKey.value.trim(),
    opentypeless_official_uid: elements.officialUid.value.trim(),
    save_video: false,
    save_cover: false,
    save_images: false,
    save_transcript: elements.saveTranscript.checked,
  };
}

async function requestJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const text = await response.text();
  const data = safeJsonParse(text);
  if (!response.ok) {
    throw new Error(data.detail || text || "请求失败");
  }
  return data;
}

function buildAssetUrl(kind, index = null, disposition = "inline") {
  if (!state.lastText) {
    return "";
  }
  const params = new URLSearchParams({
    text: state.lastText,
    kind,
    disposition,
  });
  if (index !== null && index !== undefined) {
    params.set("index", String(index));
  }
  return `/api/asset?${params.toString()}`;
}

function setEmptyPreview(message) {
  elements.previewGrid.className = "preview-grid empty-state";
  elements.previewGrid.innerHTML = `<p>${message}</p>`;
}

function renderSummary(media, meta = {}) {
  elements.resultSummary.innerHTML = "";
  elements.resultSummary.className = "summary-grid";

  const entries = [
    ["平台", media.platform || "-"],
    ["标题", media.title || "-"],
    ["视频 ID", media.video_id || "-"],
    ["内容类型", media.is_image_post ? "图集" : "视频"],
  ];

  if (meta.backend) {
    entries.push(["转写后端", meta.backend]);
  }
  if (meta.model) {
    entries.push(["转写模型", meta.model]);
  }
  if (meta.mode) {
    entries.push(["识别模式", meta.mode]);
  }
  if (meta.output_dir) {
    entries.push(["输出目录", meta.output_dir]);
  }

  for (const [key, value] of entries) {
    const fragment = elements.summaryTemplate.content.cloneNode(true);
    fragment.querySelector(".summary-key").textContent = key;
    fragment.querySelector(".summary-value").textContent = value || "-";
    elements.resultSummary.appendChild(fragment);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function createActionLinks(kind, index = null, rawUrl = "") {
  const inlineUrl = buildAssetUrl(kind, index, "inline");
  const downloadUrl = buildAssetUrl(kind, index, "attachment");
  const copyValue = rawUrl || inlineUrl;

  return `
    <div class="asset-actions">
      <a class="asset-button primary" href="${downloadUrl}">下载</a>
      <a class="asset-button" href="${inlineUrl}" target="_blank" rel="noreferrer">打开</a>
      <button class="asset-button copy-button" type="button" data-copy="${escapeHtml(copyValue)}">复制地址</button>
    </div>
  `;
}

function renderPreview(media) {
  const cards = [];

  if (media.video_url) {
    cards.push(`
      <article class="preview-card preview-card-wide">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">视频</span>
            <h3>视频预览</h3>
          </div>
        </div>
        <video class="media-player" controls playsinline preload="metadata" src="${buildAssetUrl("video")}"></video>
        <p class="asset-url">${escapeHtml(media.video_url)}</p>
        ${createActionLinks("video", null, media.video_url)}
      </article>
    `);
  }

  if (media.audio_url) {
    cards.push(`
      <article class="preview-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">音频</span>
            <h3>音频预览</h3>
          </div>
        </div>
        <audio class="audio-player" controls preload="metadata" src="${buildAssetUrl("audio")}"></audio>
        <p class="asset-url">${escapeHtml(media.audio_url)}</p>
        ${createActionLinks("audio", null, media.audio_url)}
      </article>
    `);
  }

  if (media.cover_url) {
    cards.push(`
      <article class="preview-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">封面</span>
            <h3>封面预览</h3>
          </div>
        </div>
        <img
          class="image-preview"
          src="${buildAssetUrl("cover")}"
          alt="内容封面预览"
          loading="lazy"
        >
        <p class="asset-url">${escapeHtml(media.cover_url)}</p>
        ${createActionLinks("cover", null, media.cover_url)}
      </article>
    `);
  }

  if (Array.isArray(media.image_list) && media.image_list.length) {
    const galleryItems = media.image_list
      .map((item, index) => {
        const previewUrl = buildAssetUrl("image", index, "inline");
        const downloadUrl = buildAssetUrl("image", index, "attachment");
        return `
          <figure class="gallery-item">
            <img src="${previewUrl}" alt="图集图片 ${index + 1}" loading="lazy">
            <figcaption>
              <span>图 ${index + 1}</span>
              <div class="gallery-actions">
                <a class="mini-button" href="${downloadUrl}">下载</a>
                <button class="mini-button copy-button" type="button" data-copy="${escapeHtml(item)}">复制地址</button>
              </div>
            </figcaption>
          </figure>
        `;
      })
      .join("");

    cards.push(`
      <article class="preview-card preview-card-wide">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">图集</span>
            <h3>图集预览</h3>
          </div>
        </div>
        <div class="gallery-grid">${galleryItems}</div>
      </article>
    `);
  }

  if (!cards.length) {
    setEmptyPreview("当前内容没有可预览资源。");
    return;
  }

  elements.previewGrid.className = "preview-grid";
  elements.previewGrid.innerHTML = cards.join("");
  bindPreviewActions();
}

function bindPreviewActions() {
  elements.previewGrid.querySelectorAll(".copy-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.getAttribute("data-copy") || "";
      if (!value) {
        return;
      }
      await navigator.clipboard.writeText(value);
      const previous = button.textContent;
      button.textContent = "已复制";
      window.setTimeout(() => {
        button.textContent = previous;
      }, 1200);
    });
  });
}

function clearResults() {
  state.lastParse = null;
  state.lastTranscript = "";
  state.lastText = "";
  elements.resultSummary.className = "summary-grid empty-state";
  elements.resultSummary.innerHTML = "<p>暂无解析结果</p>";
  setEmptyPreview("解析完成后，这里会展示视频、音频、封面和图集预览。");
  elements.transcriptOutput.textContent = "暂无转写内容";
  setStatus("idle", "等待操作", "先解析媒体信息，再查看预览或发起转写。");
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (response.ok && data.success) {
      elements.healthStatus.textContent = "在线";
      elements.healthHint.textContent = "接口正常，可以开始处理媒体。";
      return;
    }
    throw new Error("健康检查失败");
  } catch {
    elements.healthStatus.textContent = "异常";
    elements.healthHint.textContent = "无法连接到后端接口。";
  }
}

async function handleParse() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先输入分享文案或链接。");
    return;
  }

  setStatus("loading", "正在解析", "正在读取媒体元数据并生成预览入口。");
  try {
    const result = await requestJson("/api/parse", { text: payload.text });
    state.lastText = result.data.source_url || payload.text;
    state.lastParse = result.data;
    renderSummary(result.data);
    renderPreview(result.data);
    setStatus("success", "解析完成", "资源已经可预览，你可以直接单独下载任意项。");
  } catch (error) {
    setStatus("error", "解析失败", error.message);
  }
}

async function handleExtract() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先输入分享文案或链接。");
    return;
  }

  setStatus("loading", "正在提取文案", "正在下载临时媒体、抽取音频并提交 OpenTypeless 转写。");
  try {
    const result = await requestJson("/api/extract", payload);
    state.lastText = result.data.media.source_url || payload.text;
    state.lastParse = result.data.media;
    state.lastTranscript = result.data.transcript || "";

    renderSummary(result.data.media, {
      output_dir: result.data.output_dir,
      backend: result.data.transcription?.backend,
      model: result.data.transcription?.model,
      mode: result.data.transcription?.mode,
    });
    renderPreview(result.data.media);
    elements.transcriptOutput.textContent = state.lastTranscript || "转写接口未返回内容";

    setStatus(
      "success",
      "提取完成",
      "文案已经生成，临时下载的视频和中间音频文件已在服务端自动清理。",
    );
  } catch (error) {
    setStatus("error", "提取失败", error.message);
  }
}

async function copyTranscript() {
  const text = state.lastTranscript || elements.transcriptOutput.textContent;
  if (!text || text === "暂无转写内容") {
    setStatus("error", "没有可复制内容", "请先执行文案提取。");
    return;
  }

  await navigator.clipboard.writeText(text);
  setStatus("success", "复制完成", "转写内容已复制到剪贴板。");
}

function bindEvents() {
  elements.parseAction.addEventListener("click", handleParse);
  elements.extractAction.addEventListener("click", handleExtract);
  elements.clearResults.addEventListener("click", clearResults);
  elements.copyTranscript.addEventListener("click", copyTranscript);
  elements.fillDemo.addEventListener("click", () => {
    elements.text.value = "https://www.douyin.com/video/7396822576074460467";
    setStatus("idle", "已填充示例", "现在可以直接点击解析链接。");
  });

  [
    elements.apiModel,
    elements.credentialPath,
    elements.deviceId,
    elements.token,
    elements.officialMode,
    elements.officialAppKey,
    elements.officialAccessKey,
    elements.officialUid,
  ].forEach((input) => {
    input.addEventListener("change", saveConfig);
  });

  elements.apiModel.addEventListener("change", () => syncModelFields(true));
}

restoreConfig();
bindEvents();
checkHealth();
clearResults();
