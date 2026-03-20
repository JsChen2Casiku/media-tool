const qs = (selector) => document.querySelector(selector);

const DEFAULTS = {
  transcriptionBaseUrl: "http://127.0.0.1:9000",
  transcriptionTask: "transcribe",
  transcriptionLanguage: "zh",
  transcriptionTimeout: "300",
  transcriptionEncode: true,
  transcriptionWordTimestamps: false,
  transcriptionVadFilter: false,
  saveTranscript: true,
};

const state = {
  lastParse: null,
  lastTranscript: "",
  lastText: "",
};

const elements = {
  text: qs("#media-text"),
  transcriptionBaseUrl: qs("#transcription-base-url"),
  transcriptionTask: qs("#transcription-task"),
  transcriptionLanguage: qs("#transcription-language"),
  transcriptionTimeout: qs("#transcription-timeout"),
  transcriptionEncode: qs("#transcription-encode"),
  transcriptionWordTimestamps: qs("#transcription-word-timestamps"),
  transcriptionVadFilter: qs("#transcription-vad-filter"),
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
};

function hasElement(element) {
  return element !== null && element !== undefined;
}

function setValue(element, value) {
  if (hasElement(element)) {
    element.value = value;
  }
}

function setChecked(element, value) {
  if (hasElement(element)) {
    element.checked = Boolean(value);
  }
}

function getValue(element, fallback = "") {
  return hasElement(element) ? String(element.value ?? fallback) : fallback;
}

function getTrimmedValue(element, fallback = "") {
  return getValue(element, fallback).trim();
}

function getChecked(element, fallback = false) {
  return hasElement(element) ? Boolean(element.checked) : fallback;
}

function setText(element, value) {
  if (hasElement(element)) {
    element.textContent = value;
  }
}

function setHtml(element, value) {
  if (hasElement(element)) {
    element.innerHTML = value;
  }
}

function setStatus(kind, title, message) {
  if (hasElement(elements.statusCard)) {
    elements.statusCard.className = `status-card ${kind}`;
  }
  setText(elements.statusTitle, title);
  setText(elements.statusMessage, message);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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
    transcriptionBaseUrl: getTrimmedValue(elements.transcriptionBaseUrl, DEFAULTS.transcriptionBaseUrl),
    transcriptionTask: getValue(elements.transcriptionTask, DEFAULTS.transcriptionTask),
    transcriptionLanguage: getTrimmedValue(elements.transcriptionLanguage, DEFAULTS.transcriptionLanguage),
    transcriptionTimeout: getTrimmedValue(elements.transcriptionTimeout, DEFAULTS.transcriptionTimeout),
    transcriptionEncode: getChecked(elements.transcriptionEncode, DEFAULTS.transcriptionEncode),
    transcriptionWordTimestamps: getChecked(
      elements.transcriptionWordTimestamps,
      DEFAULTS.transcriptionWordTimestamps,
    ),
    transcriptionVadFilter: getChecked(elements.transcriptionVadFilter, DEFAULTS.transcriptionVadFilter),
    saveTranscript: getChecked(elements.saveTranscript, DEFAULTS.saveTranscript),
  };
  localStorage.setItem("media-tool-config", JSON.stringify(payload));
}

function restoreConfig() {
  const parsed = safeJsonParse(localStorage.getItem("media-tool-config") || "{}");
  setValue(elements.transcriptionBaseUrl, parsed.transcriptionBaseUrl || DEFAULTS.transcriptionBaseUrl);
  setValue(elements.transcriptionTask, parsed.transcriptionTask || DEFAULTS.transcriptionTask);
  setValue(elements.transcriptionLanguage, parsed.transcriptionLanguage || DEFAULTS.transcriptionLanguage);
  setValue(elements.transcriptionTimeout, parsed.transcriptionTimeout || DEFAULTS.transcriptionTimeout);
  setChecked(elements.transcriptionEncode, parsed.transcriptionEncode ?? DEFAULTS.transcriptionEncode);
  setChecked(
    elements.transcriptionWordTimestamps,
    parsed.transcriptionWordTimestamps ?? DEFAULTS.transcriptionWordTimestamps,
  );
  setChecked(elements.transcriptionVadFilter, parsed.transcriptionVadFilter ?? DEFAULTS.transcriptionVadFilter);
  setChecked(elements.saveTranscript, parsed.saveTranscript ?? DEFAULTS.saveTranscript);
}

function buildAssetUrl(kind, index = null, disposition = "inline") {
  const url = new URL("/api/asset", window.location.origin);
  url.searchParams.set("text", state.lastText);
  url.searchParams.set("kind", kind);
  url.searchParams.set("disposition", disposition);
  if (index !== null && index !== undefined) {
    url.searchParams.set("index", String(index));
  }
  return url.toString();
}

function createDownloadLink(kind, index = null, label = "下载") {
  return `<a class="asset-button primary" href="${buildAssetUrl(kind, index, "attachment")}">${label}</a>`;
}

function createSummaryItem(label, value) {
  return `
    <article class="summary-item">
      <span class="summary-key">${escapeHtml(label)}</span>
      <strong class="summary-value">${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderSummary(media, transcription = null) {
  if (!media) {
    setHtml(elements.resultSummary, "<p>暂无解析结果</p>");
    elements.resultSummary.className = "summary-grid empty-state";
    return;
  }

  const items = [
    ["平台", media.platform || "-"],
    ["标题", media.title || "-"],
    ["视频 ID", media.video_id || "-"],
    ["内容类型", media.is_image_post ? "图集" : "视频"],
    ["原始链接", media.source_url || "-"],
    ["跳转链接", media.redirect_url || "-"],
    ["视频地址", media.video_url || "-"],
    ["音频地址", media.audio_url || "-"],
    ["封面地址", media.cover_url || "-"],
    ["图集数量", Array.isArray(media.image_list) ? String(media.image_list.length) : "0"],
  ];

  if (transcription) {
    items.push(["转写服务", transcription.base_url || "-"]);
    items.push(["检测语言", transcription.detected_language || transcription.language || "-"]);
  }

  setHtml(elements.resultSummary, items.map(([label, value]) => createSummaryItem(label, value)).join(""));
  elements.resultSummary.className = "summary-grid";
}

function renderPreview(media) {
  if (!media) {
    setHtml(elements.previewGrid, "<p>解析完成后，这里会展示视频、音频、封面和图集预览。</p>");
    elements.previewGrid.className = "preview-grid empty-state";
    return;
  }

  const cards = [];

  if (media.video_url) {
    cards.push(`
      <article class="preview-card preview-card-wide">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">VIDEO</span>
            <h3>视频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("video", null, "下载视频")}</div>
        </div>
        <video class="media-player" controls preload="metadata" src="${buildAssetUrl("video")}"></video>
        <p class="asset-url">${escapeHtml(media.video_url)}</p>
      </article>
    `);
  }

  if (media.audio_url) {
    cards.push(`
      <article class="preview-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">AUDIO</span>
            <h3>音频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("audio", null, "下载音频")}</div>
        </div>
        <audio class="audio-player" controls preload="metadata" src="${buildAssetUrl("audio")}"></audio>
        <p class="asset-url">${escapeHtml(media.audio_url)}</p>
      </article>
    `);
  }

  if (media.cover_url) {
    cards.push(`
      <article class="preview-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">COVER</span>
            <h3>封面预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("cover", null, "下载封面")}</div>
        </div>
        <img class="image-preview" alt="封面预览" src="${buildAssetUrl("cover")}">
        <p class="asset-url">${escapeHtml(media.cover_url)}</p>
      </article>
    `);
  }

  if (Array.isArray(media.image_list) && media.image_list.length > 0) {
    const gallery = media.image_list
      .map((imageUrl, index) => {
        return `
          <figure class="gallery-item">
            <img alt="图集 ${index + 1}" src="${buildAssetUrl("image", index)}">
            <figcaption>
              <span>图集 ${index + 1}</span>
              <div class="gallery-actions">
                <a class="mini-button" href="${buildAssetUrl("image", index, "attachment")}">下载图片</a>
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
            <span class="preview-type">GALLERY</span>
            <h3>图集预览</h3>
          </div>
        </div>
        <div class="gallery-grid">${gallery}</div>
      </article>
    `);
  }

  if (cards.length === 0) {
    setHtml(elements.previewGrid, "<p>当前媒体没有可预览资源。</p>");
    elements.previewGrid.className = "preview-grid empty-state";
    return;
  }

  setHtml(elements.previewGrid, cards.join(""));
  elements.previewGrid.className = "preview-grid";
}

function renderTranscript(text, transcription = null) {
  const blocks = [];
  if (transcription) {
    blocks.push(`转写服务: ${transcription.base_url || "-"}`);
    blocks.push(`转写任务: ${transcription.task || "-"}`);
    blocks.push(`检测语言: ${transcription.detected_language || transcription.language || "-"}`);
    blocks.push(`分段数量: ${transcription.segment_count ?? "-"}`);
    blocks.push("");
  }
  blocks.push(text || "暂无转写内容");
  setText(elements.transcriptOutput, blocks.join("\n"));
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  const payload = text ? safeJsonParse(text) : {};

  if (!response.ok) {
    throw new Error(payload.detail || payload.message || text || `请求失败: HTTP ${response.status}`);
  }
  return payload;
}

function getCommonPayload() {
  saveConfig();
  return {
    text: getTrimmedValue(elements.text),
    transcription_base_url: getTrimmedValue(elements.transcriptionBaseUrl, DEFAULTS.transcriptionBaseUrl),
    transcription_task: getValue(elements.transcriptionTask, DEFAULTS.transcriptionTask),
    transcription_language: getTrimmedValue(elements.transcriptionLanguage, DEFAULTS.transcriptionLanguage),
    transcription_timeout: Number.parseInt(
      getTrimmedValue(elements.transcriptionTimeout, DEFAULTS.transcriptionTimeout),
      10,
    ),
    transcription_encode: getChecked(elements.transcriptionEncode, DEFAULTS.transcriptionEncode),
    transcription_word_timestamps: getChecked(
      elements.transcriptionWordTimestamps,
      DEFAULTS.transcriptionWordTimestamps,
    ),
    transcription_vad_filter: getChecked(elements.transcriptionVadFilter, DEFAULTS.transcriptionVadFilter),
    save_transcript: getChecked(elements.saveTranscript, DEFAULTS.saveTranscript),
  };
}

async function checkHealth() {
  try {
    await requestJson("/api/health", { method: "GET" });
    setText(elements.healthStatus, "在线");
    setText(elements.healthHint, "HTTP API 可用，已就绪。");
  } catch (error) {
    setText(elements.healthStatus, "异常");
    setText(elements.healthHint, error.message);
  }
}

async function parseMedia() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  setStatus("loading", "正在解析", "正在请求解析接口并生成媒体预览。");

  try {
    const result = await requestJson("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: payload.text }),
    });

    state.lastParse = result.data;
    state.lastText = payload.text;
    renderSummary(result.data);
    renderPreview(result.data);
    setStatus("success", "解析完成", "媒体信息已更新，可以直接预览或继续提取文案。");
  } catch (error) {
    setStatus("error", "解析失败", error.message);
  }
}

async function extractTranscript() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  setStatus("loading", "正在提取文案", "正在下载临时媒体并提交 Whisper ASR 转写，完成后会自动清理临时文件。");

  try {
    const result = await requestJson("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    state.lastParse = result.data.media;
    state.lastText = payload.text;
    state.lastTranscript = result.data.transcript || "";

    renderSummary(result.data.media, result.data.transcription);
    renderPreview(result.data.media);
    renderTranscript(state.lastTranscript, result.data.transcription);
    setStatus("success", "转写完成", "文案已生成，可以复制结果或保存 transcript.md。");
  } catch (error) {
    setStatus("error", "转写失败", error.message);
  }
}

function fillDemo() {
  setValue(elements.text, "https://www.douyin.com/video/7396822576074460467");
}

function clearResults() {
  state.lastParse = null;
  state.lastTranscript = "";
  state.lastText = "";
  renderSummary(null);
  renderPreview(null);
  renderTranscript("");
  setStatus("idle", "等待操作", "先解析媒体信息，再查看预览或发起转写。");
}

async function copyTranscript() {
  if (!state.lastTranscript) {
    setStatus("error", "没有可复制内容", "请先执行一次文案提取。");
    return;
  }

  try {
    await navigator.clipboard.writeText(state.lastTranscript);
    setStatus("success", "复制成功", "文案已经复制到剪贴板。");
  } catch (error) {
    setStatus("error", "复制失败", error.message || "浏览器拒绝了剪贴板操作。");
  }
}

function bindEvents() {
  elements.parseAction?.addEventListener("click", parseMedia);
  elements.extractAction?.addEventListener("click", extractTranscript);
  elements.fillDemo?.addEventListener("click", fillDemo);
  elements.clearResults?.addEventListener("click", clearResults);
  elements.copyTranscript?.addEventListener("click", copyTranscript);

  [
    elements.transcriptionBaseUrl,
    elements.transcriptionTask,
    elements.transcriptionLanguage,
    elements.transcriptionTimeout,
    elements.transcriptionEncode,
    elements.transcriptionWordTimestamps,
    elements.transcriptionVadFilter,
    elements.saveTranscript,
  ].forEach((element) => {
    if (hasElement(element)) {
      element.addEventListener("change", saveConfig);
    }
  });
}

restoreConfig();
bindEvents();
checkHealth();
clearResults();
