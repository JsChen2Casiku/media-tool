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

const POLL_INTERVAL_MS = 2000;

const state = {
  currentJobId: null,
  currentJobLogs: [],
  lastParse: null,
  lastText: "",
  lastTranscript: "",
  pollTimer: null,
  pollInFlight: false,
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
  clearResults: qs("#clear-results"),
  fillDemo: qs("#fill-demo"),
  copyLog: qs("#copy-log"),
  copyTranscript: qs("#copy-transcript"),
  statusCard: qs("#status-card"),
  statusTitle: qs("#status-title"),
  statusMessage: qs("#status-message"),
  healthStatus: qs("#health-status"),
  healthHint: qs("#health-hint"),
  jobStatus: qs("#job-status"),
  jobHint: qs("#job-hint"),
  mediaInfo: qs("#media-info"),
  previewGrid: qs("#preview-grid"),
  logOutput: qs("#log-output"),
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

function setClassName(element, value) {
  if (hasElement(element)) {
    element.className = value;
  }
}

function toggleDisabled(disabled) {
  [elements.parseAction, elements.extractAction].forEach((element) => {
    if (hasElement(element)) {
      element.disabled = disabled;
    }
  });
}

function setStatus(kind, title, message) {
  setClassName(elements.statusCard, `status-panel status-${kind}`);
  setText(elements.statusTitle, title);
  setText(elements.statusMessage, message);
}

function setJobBadge(title, hint) {
  setText(elements.jobStatus, title);
  setText(elements.jobHint, hint);
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

function appendLocalLog(message) {
  const nextLines = [...state.currentJobLogs, `[${new Date().toLocaleTimeString("zh-CN", { hour12: false })}] ${message}`];
  renderLogs(nextLines);
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
  const stored = safeJsonParse(localStorage.getItem("media-tool-config") || "{}");
  setValue(elements.transcriptionBaseUrl, stored.transcriptionBaseUrl || DEFAULTS.transcriptionBaseUrl);
  setValue(elements.transcriptionTask, stored.transcriptionTask || DEFAULTS.transcriptionTask);
  setValue(elements.transcriptionLanguage, stored.transcriptionLanguage || DEFAULTS.transcriptionLanguage);
  setValue(elements.transcriptionTimeout, stored.transcriptionTimeout || DEFAULTS.transcriptionTimeout);
  setChecked(elements.transcriptionEncode, stored.transcriptionEncode ?? DEFAULTS.transcriptionEncode);
  setChecked(
    elements.transcriptionWordTimestamps,
    stored.transcriptionWordTimestamps ?? DEFAULTS.transcriptionWordTimestamps,
  );
  setChecked(elements.transcriptionVadFilter, stored.transcriptionVadFilter ?? DEFAULTS.transcriptionVadFilter);
  setChecked(elements.saveTranscript, stored.saveTranscript ?? DEFAULTS.saveTranscript);
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

function createDownloadLink(kind, label, index = null) {
  return `<a class="asset-link" href="${buildAssetUrl(kind, index, "attachment")}">${escapeHtml(label)}</a>`;
}

function createInfoItem(label, value, wide = false) {
  return `
    <article class="info-item ${wide ? "is-wide" : ""}">
      <span class="item-label">${escapeHtml(label)}</span>
      <strong class="item-value">${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderMediaInfo(media, transcription = null) {
  if (!media) {
    setHtml(elements.mediaInfo, "<p>暂无媒体信息</p>");
    setClassName(elements.mediaInfo, "info-grid info-empty");
    return;
  }

  const items = [
    createInfoItem("平台", media.platform || "-"),
    createInfoItem("类型", media.is_image_post ? "图集" : "视频"),
    createInfoItem("视频 ID", media.video_id || "-"),
    createInfoItem("图集数量", Array.isArray(media.image_list) ? String(media.image_list.length) : "0"),
    createInfoItem("标题", media.title || "-", true),
  ];

  if (transcription) {
    items.push(createInfoItem("转写语言", transcription.detected_language || transcription.language || "-", false));
    items.push(createInfoItem("分段数量", String(transcription.segment_count ?? "-"), false));
    items.push(createInfoItem("转写服务", transcription.base_url || "-", true));
  }

  setHtml(elements.mediaInfo, items.join(""));
  setClassName(elements.mediaInfo, "info-grid");
}

function renderPreview(media) {
  if (!media) {
    setHtml(elements.previewGrid, "<p>解析完成后，这里会显示视频、音频、封面和图集预览。</p>");
    setClassName(elements.previewGrid, "preview-root preview-empty");
    return;
  }

  const videoBlock = media.video_url
    ? `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Video</p>
            <h3>视频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("video", "下载视频")}</div>
        </div>
        <video class="preview-video" controls preload="metadata" src="${buildAssetUrl("video")}"></video>
      </article>
    `
    : `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Video</p>
            <h3>视频预览</h3>
          </div>
        </div>
        <div class="asset-placeholder">当前内容没有可预览的视频资源</div>
      </article>
    `;

  const audioBlock = media.audio_url
    ? `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Audio</p>
            <h3>音频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("audio", "下载音频")}</div>
        </div>
        <audio class="preview-audio" controls preload="metadata" src="${buildAssetUrl("audio")}"></audio>
      </article>
    `
    : `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Audio</p>
            <h3>音频预览</h3>
          </div>
        </div>
        <div class="asset-placeholder">当前内容没有可预览的音频资源</div>
      </article>
    `;

  const coverBlock = media.cover_url
    ? `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Cover</p>
            <h3>封面预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("cover", "下载封面")}</div>
        </div>
        <img class="preview-cover" alt="封面预览" src="${buildAssetUrl("cover")}">
      </article>
    `
    : `
      <article class="asset-card">
        <div class="asset-head">
          <div>
            <p class="preview-label">Cover</p>
            <h3>封面预览</h3>
          </div>
        </div>
        <div class="asset-placeholder">当前内容没有可预览的封面资源</div>
      </article>
    `;

  let galleryBlock = "";
  if (Array.isArray(media.image_list) && media.image_list.length > 0) {
    const galleryItems = media.image_list
      .map((_, index) => {
        return `
          <figure class="gallery-item">
            <img alt="图集 ${index + 1}" src="${buildAssetUrl("image", index)}">
            <figcaption>
              <span>图集 ${index + 1}</span>
              ${createDownloadLink("image", "下载图片", index)}
            </figcaption>
          </figure>
        `;
      })
      .join("");

    galleryBlock = `
      <section class="gallery-section">
        <div class="subsection-head">
          <h3>图集预览</h3>
        </div>
        <div class="gallery-grid">${galleryItems}</div>
      </section>
    `;
  }

  setHtml(
    elements.previewGrid,
    `
      <div class="preview-layout">
        ${videoBlock}
        <div class="preview-stack">
          ${audioBlock}
          ${coverBlock}
        </div>
      </div>
      ${galleryBlock}
    `,
  );
  setClassName(elements.previewGrid, "preview-root");
}

function renderTranscript(text, transcription = null) {
  const lines = [];
  if (transcription) {
    lines.push(`转写服务: ${transcription.base_url || "-"}`);
    lines.push(`转写任务: ${transcription.task || "-"}`);
    lines.push(`转写语言: ${transcription.detected_language || transcription.language || "-"}`);
    lines.push(`分段数量: ${transcription.segment_count ?? "-"}`);
    lines.push("");
  }
  lines.push(text || "暂无转写内容");
  state.lastTranscript = text || "";
  setText(elements.transcriptOutput, lines.join("\n"));
}

function renderLogs(lines) {
  state.currentJobLogs = Array.isArray(lines) ? [...lines] : [];
  const content = state.currentJobLogs.length > 0 ? state.currentJobLogs.join("\n") : "暂无任务日志";
  setText(elements.logOutput, content);
  if (hasElement(elements.logOutput)) {
    elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const raw = await response.text();
  const payload = raw ? safeJsonParse(raw) : {};
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || raw || `请求失败: HTTP ${response.status}`);
  }
  return payload;
}

function getPayload() {
  saveConfig();
  return {
    text: getTrimmedValue(elements.text),
    save_transcript: getChecked(elements.saveTranscript, DEFAULTS.saveTranscript),
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
    save_video: false,
    save_cover: false,
    save_images: false,
  };
}

function resetResultViews() {
  renderMediaInfo(null);
  renderPreview(null);
  renderTranscript("");
  renderLogs([]);
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.pollInFlight = false;
}

async function fetchParsedMedia(text) {
  const response = await requestJson("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return response.data;
}

async function ensureParsedMedia(text) {
  if (state.lastParse && state.lastText === text) {
    return state.lastParse;
  }
  const media = await fetchParsedMedia(text);
  state.lastText = text;
  state.lastParse = media;
  renderMediaInfo(media);
  renderPreview(media);
  return media;
}

function consumeJobResult(job) {
  if (!job || !job.result) {
    return;
  }
  const result = job.result;
  if (result.media) {
    state.lastParse = result.media;
    renderMediaInfo(result.media, result.transcription || null);
    renderPreview(result.media);
  }
  renderTranscript(result.transcript || "", result.transcription || null);
}

function applyJobState(job) {
  if (!job) {
    return;
  }

  renderLogs(job.logs || []);

  if (job.status === "queued") {
    setJobBadge("排队中", "任务已创建，等待后台执行");
    setStatus("loading", "任务排队中", "后台已接收转写任务，正在等待调度。");
    return;
  }

  if (job.status === "running") {
    setJobBadge("执行中", "日志会自动刷新，可继续轮询查看结果");
    setStatus("loading", "正在转写", "后台正在下载媒体并调用 ASR 服务。");
    return;
  }

  if (job.status === "succeeded") {
    stopPolling();
    consumeJobResult(job);
    setJobBadge("已完成", "转写任务已完成，结果已同步到页面");
    setStatus("success", "转写完成", "媒体预览和转写文案已经更新。");
    return;
  }

  if (job.status === "failed") {
    stopPolling();
    setJobBadge("失败", "任务执行失败，请查看日志定位问题");
    setStatus("error", "转写失败", job.error || "后台任务执行失败。");
    if (job.error) {
      appendLocalLog(`错误: ${job.error}`);
    }
  }
}

async function pollJobOnce() {
  if (!state.currentJobId || state.pollInFlight) {
    return;
  }

  state.pollInFlight = true;
  try {
    const response = await requestJson(`/api/jobs/${state.currentJobId}`, { method: "GET" });
    applyJobState(response.data);
  } catch (error) {
    stopPolling();
    appendLocalLog(`轮询失败: ${error.message}`);
    setJobBadge("异常", "轮询接口失败");
    setStatus("error", "轮询失败", error.message);
  } finally {
    state.pollInFlight = false;
  }
}

function startPolling(jobId) {
  stopPolling();
  state.currentJobId = jobId;
  state.pollTimer = window.setInterval(() => {
    void pollJobOnce();
  }, POLL_INTERVAL_MS);
  void pollJobOnce();
}

async function checkHealth() {
  try {
    await requestJson("/api/health", { method: "GET" });
    setText(elements.healthStatus, "在线");
    setText(elements.healthHint, "HTTP API 正常，可执行解析与转写");
  } catch (error) {
    setText(elements.healthStatus, "异常");
    setText(elements.healthHint, error.message);
  }
}

async function parseMedia() {
  const payload = getPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  stopPolling();
  state.currentJobId = null;
  toggleDisabled(true);
  setJobBadge("空闲", "当前没有后台转写任务");
  setStatus("loading", "正在解析", "正在请求解析接口并刷新媒体预览。");

  try {
    const media = await fetchParsedMedia(payload.text);
    state.lastText = payload.text;
    state.lastParse = media;
    renderMediaInfo(media);
    renderPreview(media);
    renderTranscript("");
    renderLogs([]);
    setStatus("success", "解析完成", "媒体信息与资源预览已更新。");
  } catch (error) {
    resetResultViews();
    setStatus("error", "解析失败", error.message);
  } finally {
    toggleDisabled(false);
  }
}

async function extractTranscript() {
  const payload = getPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  toggleDisabled(true);
  setStatus("loading", "准备提交", "正在校验媒体信息并创建异步转写任务。");

  try {
    await ensureParsedMedia(payload.text);
    renderTranscript("正在等待异步转写结果...");

    const response = await requestJson("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const job = response.data;
    state.currentJobId = job.job_id;
    renderLogs(job.logs || []);
    setJobBadge("排队中", `任务 ID: ${job.job_id}`);
    setStatus("loading", "任务已创建", "后台已开始执行转写，请等待轮询结果。");
    startPolling(job.job_id);
  } catch (error) {
    appendLocalLog(`创建任务失败: ${error.message}`);
    setStatus("error", "任务创建失败", error.message);
  } finally {
    toggleDisabled(false);
  }
}

function clearResults() {
  stopPolling();
  state.currentJobId = null;
  state.currentJobLogs = [];
  state.lastParse = null;
  state.lastText = "";
  state.lastTranscript = "";
  setValue(elements.text, "");
  if (hasElement(elements.text)) {
    elements.text.focus();
  }
  resetResultViews();
  setStatus("idle", "等待操作", "先解析媒体信息，再创建异步转写任务。");
  setJobBadge("空闲", "尚未创建转写任务");
}

async function copyText(text, successMessage) {
  const content = String(text || "").trim();
  if (!content) {
    setStatus("error", "复制失败", "当前没有可复制的内容。");
    return;
  }

  try {
    await navigator.clipboard.writeText(content);
    setStatus("success", "复制成功", successMessage);
  } catch (error) {
    setStatus("error", "复制失败", error.message || "浏览器拒绝访问剪贴板。");
  }
}

function fillDemo() {
  setValue(elements.text, "https://www.douyin.com/video/7396822576074460467");
}

function bindEvents() {
  if (hasElement(elements.parseAction)) {
    elements.parseAction.addEventListener("click", () => {
      void parseMedia();
    });
  }

  if (hasElement(elements.extractAction)) {
    elements.extractAction.addEventListener("click", () => {
      void extractTranscript();
    });
  }

  if (hasElement(elements.clearResults)) {
    elements.clearResults.addEventListener("click", clearResults);
  }

  if (hasElement(elements.fillDemo)) {
    elements.fillDemo.addEventListener("click", fillDemo);
  }

  if (hasElement(elements.copyLog)) {
    elements.copyLog.addEventListener("click", () => {
      void copyText(state.currentJobLogs.join("\n"), "任务日志已复制到剪贴板。");
    });
  }

  if (hasElement(elements.copyTranscript)) {
    elements.copyTranscript.addEventListener("click", () => {
      void copyText(state.lastTranscript, "转写文案已复制到剪贴板。");
    });
  }

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

function init() {
  restoreConfig();
  clearResults();
  bindEvents();
  void checkHealth();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
