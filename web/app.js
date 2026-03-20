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
  lastParse: null,
  lastTranscript: "",
  lastText: "",
  currentJobId: null,
  currentJobLogs: [],
  pollTimer: null,
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
  copyLog: qs("#copy-log"),
  statusTitle: qs("#status-title"),
  statusMessage: qs("#status-message"),
  statusCard: qs("#status-card"),
  healthStatus: qs("#health-status"),
  healthHint: qs("#health-hint"),
  jobStatus: qs("#job-status"),
  jobHint: qs("#job-hint"),
  mediaInfo: qs("#media-info"),
  previewGrid: qs("#preview-grid"),
  transcriptOutput: qs("#transcript-output"),
  logOutput: qs("#log-output"),
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

function setJobBadge(status, hint) {
  setText(elements.jobStatus, status);
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

function createMetaItem(label, value, wide = false) {
  return `
    <article class="meta-item ${wide ? "wide" : ""}">
      <span class="meta-label">${escapeHtml(label)}</span>
      <strong class="meta-value">${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderMediaInfo(media, transcription = null) {
  if (!media) {
    setHtml(elements.mediaInfo, "<p>暂无媒体信息</p>");
    elements.mediaInfo.className = "meta-grid empty-state";
    return;
  }

  const items = [
    createMetaItem("平台", media.platform || "-"),
    createMetaItem("类型", media.is_image_post ? "图集" : "视频"),
    createMetaItem("视频 ID", media.video_id || "-"),
    createMetaItem("图集数量", Array.isArray(media.image_list) ? String(media.image_list.length) : "0"),
    createMetaItem("标题", media.title || "-", true),
  ];

  if (transcription) {
    items.push(createMetaItem("转写服务", transcription.base_url || "-", true));
    items.push(createMetaItem("检测语言", transcription.detected_language || transcription.language || "-"));
    items.push(createMetaItem("分段数量", String(transcription.segment_count ?? "-")));
  }

  setHtml(elements.mediaInfo, items.join(""));
  elements.mediaInfo.className = "meta-grid";
}

function renderPreview(media) {
  if (!media) {
    setHtml(elements.previewGrid, "<p>解析完成后，这里会展示视频、音频、封面和图集预览。</p>");
    elements.previewGrid.className = "preview-area empty-state";
    return;
  }

  const videoCard = media.video_url
    ? `
      <article class="preview-card video-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">VIDEO</span>
            <h3>视频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("video", null, "下载视频")}</div>
        </div>
        <video class="media-player compact-video" controls preload="metadata" src="${buildAssetUrl("video")}"></video>
      </article>
    `
    : `
      <article class="preview-card video-card empty-preview">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">VIDEO</span>
            <h3>视频预览</h3>
          </div>
        </div>
        <div class="placeholder-box">当前内容没有视频资源</div>
      </article>
    `;

  const audioCard = media.audio_url
    ? `
      <article class="preview-card small-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">AUDIO</span>
            <h3>音频预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("audio", null, "下载音频")}</div>
        </div>
        <audio class="audio-player" controls preload="metadata" src="${buildAssetUrl("audio")}"></audio>
      </article>
    `
    : `
      <article class="preview-card small-card empty-preview">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">AUDIO</span>
            <h3>音频预览</h3>
          </div>
        </div>
        <div class="placeholder-box">当前内容没有音频资源</div>
      </article>
    `;

  const coverCard = media.cover_url
    ? `
      <article class="preview-card small-card">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">COVER</span>
            <h3>封面预览</h3>
          </div>
          <div class="asset-actions">${createDownloadLink("cover", null, "下载封面")}</div>
        </div>
        <img class="image-preview compact-cover" alt="封面预览" src="${buildAssetUrl("cover")}">
      </article>
    `
    : `
      <article class="preview-card small-card empty-preview">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">COVER</span>
            <h3>封面预览</h3>
          </div>
        </div>
        <div class="placeholder-box">当前内容没有封面资源</div>
      </article>
    `;

  let gallerySection = "";
  if (Array.isArray(media.image_list) && media.image_list.length > 0) {
    const gallery = media.image_list
      .map((_, index) => {
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

    gallerySection = `
      <section class="gallery-section">
        <div class="preview-card-head">
          <div>
            <span class="preview-type">GALLERY</span>
            <h3>图集预览</h3>
          </div>
        </div>
        <div class="gallery-grid">${gallery}</div>
      </section>
    `;
  }

  setHtml(
    elements.previewGrid,
    `
      <div class="preview-layout">
        ${videoCard}
        <div class="preview-stack">
          ${audioCard}
          ${coverCard}
        </div>
      </div>
      ${gallerySection}
    `,
  );
  elements.previewGrid.className = "preview-area";
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

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
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
  stopPolling();

  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  setStatus("loading", "正在解析", "正在请求解析接口并生成媒体预览。");
  setJobBadge("空闲", "当前没有后台转写任务");

  try {
    const result = await requestJson("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: payload.text }),
    });

    state.lastParse = result.data;
    state.lastText = payload.text;
    state.lastTranscript = "";
    state.currentJobId = null;
    renderMediaInfo(result.data);
    renderPreview(result.data);
    renderTranscript("");
    renderLogs([]);
    setStatus("success", "解析完成", "媒体信息已更新，可以直接预览或发起异步转写任务。");
  } catch (error) {
    setStatus("error", "解析失败", error.message);
  }
}

function updateFromJob(job) {
  state.currentJobId = job.job_id;
  renderLogs(job.logs);

  const lastLog = Array.isArray(job.logs) && job.logs.length > 0 ? job.logs[job.logs.length - 1] : "暂无日志";

  if (job.status === "queued") {
    setJobBadge("排队中", `任务 ID: ${job.job_id}`);
    setStatus("loading", "任务已提交", lastLog);
    return;
  }

  if (job.status === "running") {
    setJobBadge("执行中", `任务 ID: ${job.job_id}`);
    setStatus("loading", "后台转写中", lastLog);
    return;
  }

  if (job.status === "failed") {
    stopPolling();
    setJobBadge("失败", `任务 ID: ${job.job_id}`);
    setStatus("error", "转写失败", job.error || lastLog);
    return;
  }

  if (job.status === "succeeded" && job.result) {
    stopPolling();
    setJobBadge("完成", `任务 ID: ${job.job_id}`);
    state.lastParse = job.result.media;
    state.lastTranscript = job.result.transcript || "";
    renderMediaInfo(job.result.media, job.result.transcription);
    renderPreview(job.result.media);
    renderTranscript(state.lastTranscript, job.result.transcription);
    setStatus("success", "转写完成", lastLog);
  }
}

async function pollJob(jobId) {
  const result = await requestJson(`/api/jobs/${jobId}`, { method: "GET" });
  updateFromJob(result.data);
}

function startPolling(jobId) {
  stopPolling();
  pollJob(jobId).catch((error) => {
    stopPolling();
    setStatus("error", "轮询失败", error.message);
  });

  state.pollTimer = window.setInterval(async () => {
    try {
      await pollJob(jobId);
    } catch (error) {
      stopPolling();
      setStatus("error", "轮询失败", error.message);
    }
  }, POLL_INTERVAL_MS);
}

async function extractTranscript() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先粘贴分享文案或媒体链接。");
    return;
  }

  setStatus("loading", "正在创建任务", "转写任务会在后台执行，页面会自动轮询结果。");

  try {
    const result = await requestJson("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const job = result.data;
    state.lastText = payload.text;
    renderLogs(job.logs);
    setJobBadge("排队中", `任务 ID: ${job.job_id}`);
    setStatus("loading", "任务已提交", "后台任务已创建，正在等待执行。");
    startPolling(job.job_id);
  } catch (error) {
    setStatus("error", "任务创建失败", error.message);
  }
}

function fillDemo() {
  setValue(elements.text, "https://www.douyin.com/video/7396822576074460467");
}

function clearResults() {
  stopPolling();
  state.lastParse = null;
  state.lastTranscript = "";
  state.lastText = "";
  state.currentJobId = null;
  state.currentJobLogs = [];
  renderMediaInfo(null);
  renderPreview(null);
  renderTranscript("");
  renderLogs([]);
  setJobBadge("空闲", "尚未创建转写任务");
  setStatus("idle", "等待操作", "先解析媒体信息，再发起异步转写任务。");
}

async function copyTranscript() {
  if (!state.lastTranscript) {
    setStatus("error", "没有可复制内容", "请先执行一次转写任务。");
    return;
  }

  try {
    await navigator.clipboard.writeText(state.lastTranscript);
    setStatus("success", "复制成功", "文案已经复制到剪贴板。");
  } catch (error) {
    setStatus("error", "复制失败", error.message || "浏览器拒绝了剪贴板操作。");
  }
}

async function copyLog() {
  if (!state.currentJobLogs.length) {
    setStatus("error", "没有可复制日志", "当前还没有任务日志。");
    return;
  }

  try {
    await navigator.clipboard.writeText(state.currentJobLogs.join("\n"));
    setStatus("success", "复制成功", "任务日志已经复制到剪贴板。");
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
  elements.copyLog?.addEventListener("click", copyLog);

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
