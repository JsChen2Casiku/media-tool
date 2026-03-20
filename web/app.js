const qs = (selector) => document.querySelector(selector);

const DEFAULTS = {
  transcriptionBaseUrl: "http://127.0.0.1:9000",
  transcriptionTask: "transcribe",
  transcriptionLanguage: "zh",
  transcriptionTimeout: "300",
  transcriptionEncode: true,
  transcriptionWordTimestamps: false,
  transcriptionVadFilter: false,
  llmApiBase: "https://api.openai.com/v1",
  llmApiKey: "",
  llmModel: "gpt-5.4",
  llmTimeout: "90",
  saveTranscript: true,
  theme: "system",
};

const POLL_INTERVAL_MS = 2000;

const state = {
  currentJobId: null,
  currentJobLogs: [],
  lastParse: null,
  lastText: "",
  lastTranscript: "",
  selectedGalleryIndex: 0,
  lightboxItems: [],
  lightboxIndex: 0,
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
  llmApiBase: qs("#llm-api-base"),
  llmApiKey: qs("#llm-api-key"),
  llmModel: qs("#llm-model"),
  llmTimeout: qs("#llm-timeout"),
  saveTranscript: qs("#save-transcript"),
  configCenterTrigger: qs("#config-center-trigger"),
  configSummary: qs("#config-summary"),
  configModal: qs("#config-modal"),
  configModalClose: qs("#config-modal-close"),
  authUsername: qs("#auth-username"),
  currentPassword: qs("#current-password"),
  newPassword: qs("#new-password"),
  confirmPassword: qs("#confirm-password"),
  changePasswordAction: qs("#change-password-action"),
  logoutAction: qs("#logout-action"),
  parseAction: qs("#parse-action"),
  extractAction: qs("#extract-action"),
  clearResults: qs("#clear-results"),
  fillDemo: qs("#fill-demo"),
  copyLog: qs("#copy-log"),
  copyTranscript: qs("#copy-transcript"),
  themeToggle: qs("#theme-toggle"),
  themeToggleIcon: qs("#theme-toggle-icon"),
  themeToggleText: qs("#theme-toggle-text"),
  themeToggleHint: qs("#theme-toggle-hint"),
  statusCard: qs("#status-card"),
  statusTitle: qs("#status-title"),
  statusMessage: qs("#status-message"),
  statusProgress: qs("#status-progress"),
  statusProgressValue: qs("#status-progress-value"),
  statusProgressBar: qs("#status-progress-bar"),
  statusProgressHint: qs("#status-progress-hint"),
  healthStatus: qs("#health-status"),
  healthHint: qs("#health-hint"),
  jobStatus: qs("#job-status"),
  jobHint: qs("#job-hint"),
  mediaInfo: qs("#media-info"),
  previewGrid: qs("#preview-grid"),
  logOutput: qs("#log-output"),
  transcriptOutput: qs("#transcript-output"),
  imageLightbox: qs("#image-lightbox"),
  lightboxLabel: qs("#lightbox-label"),
  lightboxTitle: qs("#lightbox-title"),
  lightboxCounter: qs("#lightbox-counter"),
  lightboxImage: qs("#lightbox-image"),
  lightboxDownload: qs("#lightbox-download"),
  lightboxClose: qs("#lightbox-close"),
  lightboxPrev: qs("#lightbox-prev"),
  lightboxNext: qs("#lightbox-next"),
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

function redirectToLogin() {
  window.location.href = "/login";
}

function openConfigModal() {
  if (!hasElement(elements.configModal)) {
    return;
  }
  elements.configModal.classList.remove("is-hidden");
  elements.configModal.setAttribute("aria-hidden", "false");
}

function closeConfigModal() {
  if (!hasElement(elements.configModal)) {
    return;
  }
  elements.configModal.classList.add("is-hidden");
  elements.configModal.setAttribute("aria-hidden", "true");
}

function hasStoredConfigChanges(config) {
  if (!config || typeof config !== "object") {
    return false;
  }
  return (
    String(config.transcriptionBaseUrl ?? DEFAULTS.transcriptionBaseUrl) !== DEFAULTS.transcriptionBaseUrl
    || String(config.transcriptionTask ?? DEFAULTS.transcriptionTask) !== DEFAULTS.transcriptionTask
    || String(config.transcriptionLanguage ?? DEFAULTS.transcriptionLanguage) !== DEFAULTS.transcriptionLanguage
    || String(config.transcriptionTimeout ?? DEFAULTS.transcriptionTimeout) !== DEFAULTS.transcriptionTimeout
    || Boolean(config.transcriptionEncode ?? DEFAULTS.transcriptionEncode) !== DEFAULTS.transcriptionEncode
    || Boolean(config.transcriptionWordTimestamps ?? DEFAULTS.transcriptionWordTimestamps) !== DEFAULTS.transcriptionWordTimestamps
    || Boolean(config.transcriptionVadFilter ?? DEFAULTS.transcriptionVadFilter) !== DEFAULTS.transcriptionVadFilter
    || String(config.llmApiBase ?? DEFAULTS.llmApiBase) !== DEFAULTS.llmApiBase
    || String(config.llmApiKey ?? DEFAULTS.llmApiKey) !== DEFAULTS.llmApiKey
    || String(config.llmModel ?? DEFAULTS.llmModel) !== DEFAULTS.llmModel
    || String(config.llmTimeout ?? DEFAULTS.llmTimeout) !== DEFAULTS.llmTimeout
    || Boolean(config.saveTranscript ?? DEFAULTS.saveTranscript) !== DEFAULTS.saveTranscript
  );
}

function updateConfigSummary(saved = false) {
  setText(elements.configSummary, saved ? "集中式配置中心已保存" : "集中式配置中心");
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

function setStatusProgress(progress = null) {
  if (!hasElement(elements.statusProgress)) {
    return;
  }

  if (!progress) {
    elements.statusProgress.classList.add("is-hidden");
    elements.statusProgress.setAttribute("aria-hidden", "true");
    setText(elements.statusProgressValue, "0%");
    setText(elements.statusProgressHint, "等待任务开始");
    if (hasElement(elements.statusProgressBar)) {
      elements.statusProgressBar.style.width = "0%";
    }
    return;
  }

  const percent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
  elements.statusProgress.classList.remove("is-hidden");
  elements.statusProgress.setAttribute("aria-hidden", "false");
  setText(elements.statusProgressValue, `${percent}%`);
  setText(elements.statusProgressHint, progress.label || "正在处理");
  if (hasElement(elements.statusProgressBar)) {
    elements.statusProgressBar.style.width = `${percent}%`;
  }
}
function getJobProgress(job) {
  if (!job) {
    return null;
  }

  if (Number.isFinite(Number(job.progress_percent))) {
    const percent = Math.max(0, Math.min(100, Number(job.progress_percent)));
    if (job.status === "failed") {
      return { percent, label: job.progress_label || job.error || "任务执行失败" };
    }
    return { percent, label: job.progress_label || `当前进度 ${percent}%` };
  }

  if (job.status === "queued") {
    return { percent: 12, label: "任务已排队" };
  }

  if (job.status === "succeeded") {
    return { percent: 100, label: "转写已完成" };
  }

  if (job.status === "failed") {
    return { percent: 100, label: "任务已终止" };
  }

  if (job.status !== "running") {
    return null;
  }

  const logText = Array.isArray(job.logs) ? job.logs.join("\n") : "";
  if (logText.includes("transcript.md")) {
    return { percent: 95, label: "正在写入结果" };
  }
  if (logText.includes("Whisper ASR") && logText.includes("完成")) {
    return { percent: 84, label: "正在整理转写结果" };
  }
  if (logText.includes("Whisper ASR")) {
    return { percent: 68, label: "ASR 正在识别音频" };
  }
  if (logText.includes("下载完成")) {
    return { percent: 42, label: "媒体已下载，准备转写" };
  }
  if (logText.includes("下载转写源文件")) {
    return { percent: 24, label: "正在下载转写源文件" };
  }
  if (logText.includes("解析完成")) {
    return { percent: 16, label: "媒体已解析" };
  }
  return { percent: 8, label: "任务已启动" };
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
    llmApiBase: getTrimmedValue(elements.llmApiBase, DEFAULTS.llmApiBase),
    llmApiKey: getValue(elements.llmApiKey, DEFAULTS.llmApiKey),
    llmModel: getTrimmedValue(elements.llmModel, DEFAULTS.llmModel),
    llmTimeout: getTrimmedValue(elements.llmTimeout, DEFAULTS.llmTimeout),
    saveTranscript: getChecked(elements.saveTranscript, DEFAULTS.saveTranscript),
    theme: localStorage.getItem("media-tool-theme") || DEFAULTS.theme,
  };
  localStorage.setItem("media-tool-config", JSON.stringify(payload));
  updateConfigSummary(true);
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
  setValue(elements.llmApiBase, stored.llmApiBase || DEFAULTS.llmApiBase);
  setValue(elements.llmApiKey, stored.llmApiKey || DEFAULTS.llmApiKey);
  setValue(elements.llmModel, stored.llmModel || DEFAULTS.llmModel);
  setValue(elements.llmTimeout, stored.llmTimeout || DEFAULTS.llmTimeout);
  setChecked(elements.saveTranscript, stored.saveTranscript ?? DEFAULTS.saveTranscript);
  updateConfigSummary(hasStoredConfigChanges(stored));
  applyTheme(stored.theme || localStorage.getItem("media-tool-theme") || DEFAULTS.theme, false);
}

function getSystemTheme() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getResolvedTheme(theme) {
  return theme === "system" ? getSystemTheme() : theme;
}

function updateThemeToggle(theme) {
  const resolvedTheme = getResolvedTheme(theme);
  const isDark = resolvedTheme === "dark";
  if (hasElement(elements.themeToggle)) {
    elements.themeToggle.setAttribute("aria-pressed", String(isDark));
    elements.themeToggle.dataset.theme = theme;
    elements.themeToggle.title = isDark ? "切换为明亮模式" : "切换为暗黑模式";
  }
  setText(elements.themeToggleIcon, isDark ? "☾" : "☀");
  setText(elements.themeToggleText, isDark ? "暗黑" : "明亮");
  setText(elements.themeToggleHint, theme === "system" ? "当前跟随系统主题" : "已使用手动主题设置");
}
function applyTheme(theme, persist = true) {
  const nextTheme = theme || DEFAULTS.theme;
  const resolvedTheme = getResolvedTheme(nextTheme);
  document.body.classList.toggle("theme-dark", resolvedTheme === "dark");
  updateThemeToggle(nextTheme);
  if (persist) {
    localStorage.setItem("media-tool-theme", nextTheme);
    saveConfig();
  }
}

function toggleTheme() {
  const currentTheme = localStorage.getItem("media-tool-theme") || DEFAULTS.theme;
  const resolvedTheme = getResolvedTheme(currentTheme);
  applyTheme(resolvedTheme === "dark" ? "light" : "dark");
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

function clampIndex(value, max) {
  if (max <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(max - 1, Number(value) || 0));
}

function normalizeGalleryIndex(media) {
  const total = Array.isArray(media?.image_list) ? media.image_list.length : 0;
  state.selectedGalleryIndex = clampIndex(state.selectedGalleryIndex, total);
  return state.selectedGalleryIndex;
}

function setSelectedGalleryIndex(index) {
  if (!state.lastParse || !Array.isArray(state.lastParse.image_list) || state.lastParse.image_list.length === 0) {
    return;
  }
  state.selectedGalleryIndex = clampIndex(index, state.lastParse.image_list.length);
  renderPreview(state.lastParse);
}

function createInfoItem(label, value, wide = false, extraClass = "") {
  return `
    <article class="info-item ${wide ? "is-wide" : ""} ${extraClass}">
      <span class="item-label">${escapeHtml(label)}</span>
      <strong class="item-value">${escapeHtml(value)}</strong>
    </article>
  `;
}

function createAuthorItems(author) {
  if (!author) {
    return [
      createInfoItem("作者头像", "-", false),
      createInfoItem("作者昵称", "-", false),
    ];
  }

  const avatar = author.avatar
    ? `<img class="author-avatar" src="${escapeHtml(author.avatar)}" alt="${escapeHtml(author.nickname || "作者头像")}">`
    : `<div class="author-avatar author-avatar-fallback">${escapeHtml((author.nickname || "?").slice(0, 1))}</div>`;

  return [
    `
      <article class="info-item author-avatar-item">
        <span class="item-label">作者头像</span>
        <div class="author-avatar-box">
          ${avatar}
        </div>
      </article>
    `,
    `
      <article class="info-item author-name-item">
        <span class="item-label">作者昵称</span>
        <div class="author-name-box">
          <strong class="item-value author-name">${escapeHtml(author.nickname || "-")}</strong>
        </div>
      </article>
    `,
  ];
}
function renderMediaInfo(media, transcription = null) {
  if (!media) {
    setHtml(elements.mediaInfo, "<p>暂无媒体信息</p>");
    setClassName(elements.mediaInfo, "info-grid info-empty");
    return;
  }

  const items = [
    createInfoItem("标题", media.title || "-", true, "title-item"),
    createInfoItem("平台", media.platform || "-"),
    createInfoItem("类型", media.is_image_post ? "图集" : "视频"),
    createInfoItem("视频 ID", media.video_id || "-"),
    ...createAuthorItems(media.author),
    createInfoItem("图集数量", Array.isArray(media.image_list) ? String(media.image_list.length) : "0"),
  ];

  setHtml(elements.mediaInfo, items.join(""));
  setClassName(elements.mediaInfo, "info-grid");
}
function renderPreview(media) {
  if (!media) {
    setHtml(elements.previewGrid, "<p>解析完成后，这里会显示视频、音频、封面和图集预览。</p>");
    setClassName(elements.previewGrid, "preview-root preview-empty");
    initInteractiveCards();
    return;
  }

  const hasGallery = Array.isArray(media.image_list) && media.image_list.length > 0;
  const galleryIndex = normalizeGalleryIndex(media);
  const galleryCounter = hasGallery ? `${galleryIndex + 1} / ${media.image_list.length}` : "0 / 0";

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
    : hasGallery
      ? `
      <article class="asset-card asset-card-gallery-main">
        <div class="asset-head">
          <div>
            <p class="preview-label">Gallery</p>
            <h3>图集主预览</h3>
          </div>
          <div class="asset-actions">
            <span class="gallery-main-counter">${galleryCounter}</span>
            ${createDownloadLink("image", "下载当前图片", galleryIndex)}
          </div>
        </div>
        <button
          class="gallery-main-button image-preview-trigger"
          type="button"
          data-lightbox-kind="gallery"
          data-index="${galleryIndex}"
          aria-label="放大查看当前图集图片"
        >
          <img
            class="preview-gallery-main"
            alt="图集主预览 ${galleryIndex + 1}"
            src="${buildAssetUrl("image", galleryIndex)}"
          >
        </button>
        <div class="gallery-main-toolbar">
          <button
            class="button button-secondary button-small gallery-step-button"
            type="button"
            data-gallery-step="-1"
            ${galleryIndex <= 0 ? "disabled" : ""}
          >上一张</button>
          <div class="gallery-main-hint">点击图片可放大查看，支持下载与切换</div>
          <button
            class="button button-secondary button-small gallery-step-button"
            type="button"
            data-gallery-step="1"
            ${galleryIndex >= media.image_list.length - 1 ? "disabled" : ""}
          >下一张</button>
        </div>
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
        <button
          class="cover-preview-button image-preview-trigger"
          type="button"
          data-lightbox-kind="cover"
          aria-label="放大查看封面"
        >
          <img class="preview-cover" alt="封面预览" src="${buildAssetUrl("cover")}">
        </button>
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
  if (hasGallery) {
    const galleryItems = media.image_list
      .map((_, index) => {
        return `
          <figure class="gallery-item ${index === galleryIndex ? "is-active" : ""}">
            <button
              class="gallery-thumb-button image-preview-trigger"
              type="button"
              data-gallery-index="${index}"
              data-lightbox-kind="gallery"
              data-index="${index}"
              aria-pressed="${index === galleryIndex ? "true" : "false"}"
              aria-label="查看图集 ${index + 1}"
            >
              <img alt="图集 ${index + 1}" src="${buildAssetUrl("image", index)}">
            </button>
            <figcaption>
              <div class="gallery-caption-row">
                <div class="gallery-meta">
                  <span class="gallery-name">图集 ${index + 1}</span>
                  <small class="gallery-note">
                    <span class="gallery-status-dot ${index === galleryIndex ? "is-active" : ""}" aria-hidden="true"></span>
                  </small>
                </div>
                ${createDownloadLink("image", "下载", index)}
              </div>
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
  initInteractiveCards();
}

function getLightboxItems(kind) {
  if (!state.lastParse) {
    return [];
  }
  if (kind === "cover" && state.lastParse.cover_url) {
    return [
      {
        label: "封面图片",
        title: state.lastParse.title || "封面预览",
        previewUrl: buildAssetUrl("cover"),
        downloadUrl: buildAssetUrl("cover", null, "attachment"),
      },
    ];
  }
  if (kind === "gallery" && Array.isArray(state.lastParse.image_list)) {
    return state.lastParse.image_list.map((_, index) => ({
      label: `图集 ${index + 1}`,
      title: state.lastParse.title || `图集 ${index + 1}`,
      previewUrl: buildAssetUrl("image", index),
      downloadUrl: buildAssetUrl("image", index, "attachment"),
    }));
  }
  return [];
}

function renderLightbox() {
  const items = state.lightboxItems;
  const hasItems = Array.isArray(items) && items.length > 0;
  if (!hasItems || !hasElement(elements.imageLightbox)) {
    return;
  }
  const index = clampIndex(state.lightboxIndex, items.length);
  state.lightboxIndex = index;
  const current = items[index];
  elements.imageLightbox.classList.remove("is-hidden");
  elements.imageLightbox.setAttribute("aria-hidden", "false");
  setText(elements.lightboxLabel, items.length > 1 ? "GALLERY VIEWER" : "IMAGE VIEWER");
  setText(elements.lightboxTitle, current.title || current.label || "图片预览");
  setText(elements.lightboxCounter, `${index + 1} / ${items.length}`);
  if (hasElement(elements.lightboxImage)) {
    elements.lightboxImage.src = current.previewUrl;
    elements.lightboxImage.alt = current.label || "放大预览";
  }
  if (hasElement(elements.lightboxDownload)) {
    elements.lightboxDownload.href = current.downloadUrl;
    elements.lightboxDownload.setAttribute("download", "");
    elements.lightboxDownload.textContent = items.length > 1 ? "下载当前图片" : "下载图片";
  }
  if (hasElement(elements.lightboxPrev)) {
    elements.lightboxPrev.disabled = index <= 0;
  }
  if (hasElement(elements.lightboxNext)) {
    elements.lightboxNext.disabled = index >= items.length - 1;
  }
}

function openLightbox(kind, index = 0) {
  const items = getLightboxItems(kind);
  if (!items.length) {
    return;
  }
  state.lightboxItems = items;
  state.lightboxIndex = clampIndex(index, items.length);
  renderLightbox();
}

function closeLightbox() {
  state.lightboxItems = [];
  state.lightboxIndex = 0;
  if (!hasElement(elements.imageLightbox)) {
    return;
  }
  elements.imageLightbox.classList.add("is-hidden");
  elements.imageLightbox.setAttribute("aria-hidden", "true");
  if (hasElement(elements.lightboxImage)) {
    elements.lightboxImage.src = "";
  }
}

function stepLightbox(offset) {
  if (!Array.isArray(state.lightboxItems) || state.lightboxItems.length <= 1) {
    return;
  }
  state.lightboxIndex = clampIndex(state.lightboxIndex + offset, state.lightboxItems.length);
  renderLightbox();
}

function bindInteractiveCard(card) {
  if (!hasElement(card) || card.dataset.glowBound === "true") {
    return;
  }

  card.dataset.glowBound = "true";
  card.classList.add("interactive-glow");

  card.addEventListener("pointermove", (event) => {
    const rect = card.getBoundingClientRect();
    const x = `${event.clientX - rect.left}px`;
    const y = `${event.clientY - rect.top}px`;
    card.style.setProperty("--glow-x", x);
    card.style.setProperty("--glow-y", y);
    card.classList.add("is-glow-active");
  });

  card.addEventListener("pointerenter", () => {
    card.classList.add("is-glow-active");
  });

  card.addEventListener("pointerleave", () => {
    card.classList.remove("is-glow-active");
  });
}

function initInteractiveCards() {
  document
    .querySelectorAll(".app-header, .preview-card, .asset-card, .gallery-item")
    .forEach((card) => bindInteractiveCard(card));
}

function renderTranscript(text, transcription = null, llmReview = null) {
  const lines = [];
  if (transcription) {
    lines.push(`转写服务: ${transcription.base_url || "-"}`);
    lines.push(`转写任务: ${transcription.task || "-"}`);
    lines.push(`转写语言: ${transcription.detected_language || transcription.language || "-"}`);
    lines.push(`分段数量: ${transcription.segment_count ?? "-"}`);
    if (llmReview) {
      lines.push(`文案校正: ${llmReview.applied ? "已启用" : llmReview.status || "未启用"}`);
      lines.push(`校正模型: ${llmReview.model || "-"}`);
    }
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
  if (response.status === 401) {
    redirectToLogin();
    throw new Error(payload.detail || "登录状态已失效，请重新登录。");
  }
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || raw || `请求失败: HTTP ${response.status}`);
  }
  return payload;
}

async function loadAuthProfile() {
  const response = await requestJson("/api/auth/config", {
    method: "GET",
  });
  setValue(elements.authUsername, response.data?.username || "");
}

async function changePassword() {
  const currentPassword = getValue(elements.currentPassword).trim();
  const newPassword = getValue(elements.newPassword).trim();
  const confirmPassword = getValue(elements.confirmPassword).trim();

  if (!currentPassword || !newPassword || !confirmPassword) {
    setStatus("error", "修改失败", "请完整填写当前密码、新密码和确认密码。");
    return;
  }

  try {
    const response = await requestJson("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
    setValue(elements.currentPassword, "");
    setValue(elements.newPassword, "");
    setValue(elements.confirmPassword, "");
    setStatus("success", "密码已更新", response.data?.message || "集中式配置中心已保存。");
    appendLocalLog("登录密码已通过配置中心更新。");
  } catch (error) {
    setStatus("error", "修改失败", error instanceof Error ? error.message : String(error));
  }
}

async function logout() {
  try {
    await requestJson("/api/auth/logout", {
      method: "POST",
    });
  } finally {
    redirectToLogin();
  }
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
    llm_api_base: getTrimmedValue(elements.llmApiBase, DEFAULTS.llmApiBase),
    llm_api_key: getValue(elements.llmApiKey, DEFAULTS.llmApiKey),
    llm_model: getTrimmedValue(elements.llmModel, DEFAULTS.llmModel),
    llm_timeout: Number.parseInt(
      getTrimmedValue(elements.llmTimeout, DEFAULTS.llmTimeout),
      10,
    ),
    save_video: false,
    save_cover: false,
    save_images: false,
  };
}

function resetResultViews() {
  state.selectedGalleryIndex = 0;
  renderMediaInfo(null);
  renderPreview(null);
  renderTranscript("");
  renderLogs([]);
  setStatusProgress(null);
  closeLightbox();
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
  state.selectedGalleryIndex = 0;
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
    state.selectedGalleryIndex = 0;
    renderMediaInfo(result.media, result.transcription || null);
    renderPreview(result.media);
  }
  renderTranscript(result.transcript || "", result.transcription || null, result.llm_review || null);
}

function applyJobState(job) {
  if (!job) {
    return;
  }

  renderLogs(job.logs || []);

  if (job.status === "queued") {
    setJobBadge("排队中", "任务已创建，等待后台执行");
    setStatus("loading", "任务排队中", "后台已接收转写任务，正在等待调度。");
    setStatusProgress(getJobProgress(job));
    return;
  }

  if (job.status === "running") {
    setJobBadge("执行中", "日志会自动刷新，可继续轮询查看结果");
    setStatus("loading", "正在转写", "后台正在下载媒体并调用 ASR 服务。");
    setStatusProgress(getJobProgress(job));
    return;
  }

  if (job.status === "succeeded") {
    stopPolling();
    consumeJobResult(job);
    setJobBadge("已完成", "转写任务已完成，结果已同步到页面");
    setStatus("success", "转写完成", "媒体预览和转写文案已经更新。");
    setStatusProgress(getJobProgress(job));
    return;
  }

  if (job.status === "failed") {
    stopPolling();
    setJobBadge("失败", "任务执行失败，请查看日志定位问题");
    setStatus("error", "转写失败", job.error || "后台任务执行失败。");
    setStatusProgress(getJobProgress(job));
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
    setStatusProgress(null);
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
    setStatusProgress(getJobProgress(job));
    startPolling(job.job_id);
  } catch (error) {
    appendLocalLog(`创建任务失败: ${error.message}`);
    setStatus("error", "任务创建失败", error.message);
    setStatusProgress(null);
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
  setStatusProgress(null);
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

function handlePreviewGridClick(event) {
  const gallerySwitch = event.target.closest("[data-gallery-index]");
  if (gallerySwitch) {
    event.preventDefault();
    const nextIndex = Number(gallerySwitch.dataset.galleryIndex);
    setSelectedGalleryIndex(nextIndex);
    openLightbox("gallery", nextIndex);
    return;
  }

  const galleryStep = event.target.closest("[data-gallery-step]");
  if (galleryStep) {
    event.preventDefault();
    setSelectedGalleryIndex(state.selectedGalleryIndex + Number(galleryStep.dataset.galleryStep || 0));
    return;
  }

  const previewTrigger = event.target.closest(".image-preview-trigger");
  if (previewTrigger) {
    event.preventDefault();
    openLightbox(previewTrigger.dataset.lightboxKind || "cover", Number(previewTrigger.dataset.index || 0));
  }
}

function handleGlobalKeydown(event) {
  if (hasElement(elements.configModal) && !elements.configModal.classList.contains("is-hidden")) {
    if (event.key === "Escape") {
      closeConfigModal();
      return;
    }
  }
  if (hasElement(elements.imageLightbox) && !elements.imageLightbox.classList.contains("is-hidden")) {
    if (event.key === "Escape") {
      closeLightbox();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      stepLightbox(-1);
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      stepLightbox(1);
    }
  }
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

  if (hasElement(elements.themeToggle)) {
    elements.themeToggle.addEventListener("click", toggleTheme);
  }

  if (hasElement(elements.configCenterTrigger)) {
    elements.configCenterTrigger.addEventListener("click", openConfigModal);
  }

  if (hasElement(elements.configModalClose)) {
    elements.configModalClose.addEventListener("click", closeConfigModal);
  }

  if (hasElement(elements.configModal)) {
    elements.configModal.addEventListener("click", (event) => {
      if (event.target instanceof HTMLElement && event.target.dataset.configClose === "true") {
        closeConfigModal();
      }
    });
  }

  if (hasElement(elements.changePasswordAction)) {
    elements.changePasswordAction.addEventListener("click", () => {
      void changePassword();
    });
  }

  if (hasElement(elements.logoutAction)) {
    elements.logoutAction.addEventListener("click", () => {
      void logout();
    });
  }

  if (hasElement(elements.previewGrid)) {
    elements.previewGrid.addEventListener("click", handlePreviewGridClick);
  }

  if (hasElement(elements.lightboxClose)) {
    elements.lightboxClose.addEventListener("click", closeLightbox);
  }

  if (hasElement(elements.imageLightbox)) {
    elements.imageLightbox.addEventListener("click", (event) => {
      if (event.target instanceof HTMLElement && event.target.dataset.lightboxClose === "true") {
        closeLightbox();
      }
    });
  }

  if (hasElement(elements.lightboxPrev)) {
    elements.lightboxPrev.addEventListener("click", () => stepLightbox(-1));
  }

  if (hasElement(elements.lightboxNext)) {
    elements.lightboxNext.addEventListener("click", () => stepLightbox(1));
  }

  document.addEventListener("keydown", handleGlobalKeydown);

  [
    elements.transcriptionBaseUrl,
    elements.transcriptionTask,
    elements.transcriptionLanguage,
    elements.transcriptionTimeout,
    elements.transcriptionEncode,
    elements.transcriptionWordTimestamps,
    elements.transcriptionVadFilter,
    elements.llmApiBase,
    elements.llmApiKey,
    elements.llmModel,
    elements.llmTimeout,
    elements.saveTranscript,
  ].forEach((element) => {
    if (hasElement(element)) {
      element.addEventListener("change", () => {
        saveConfig();
      });
    }
  });

  if (window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", () => {
      const savedTheme = localStorage.getItem("media-tool-theme") || DEFAULTS.theme;
      if (savedTheme === "system") {
        applyTheme("system", false);
      }
    });
  }
}

function init() {
  restoreConfig();
  clearResults();
  bindEvents();
  initInteractiveCards();
  void loadAuthProfile();
  void checkHealth();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
