const qs = (selector) => document.querySelector(selector);

const state = {
  lastParse: null,
  lastTranscript: "",
};

const elements = {
  text: qs("#media-text"),
  apiBase: qs("#api-base"),
  apiKey: qs("#api-key"),
  apiModel: qs("#api-model"),
  saveVideo: qs("#save-video"),
  saveCover: qs("#save-cover"),
  saveImages: qs("#save-images"),
  saveTranscript: qs("#save-transcript"),
  parseAction: qs("#parse-action"),
  downloadAction: qs("#download-action"),
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
  linkGrid: qs("#link-grid"),
  transcriptOutput: qs("#transcript-output"),
  summaryTemplate: qs("#summary-item-template"),
  linkTemplate: qs("#link-card-template"),
};

function setStatus(kind, title, message) {
  elements.statusCard.className = `status-card ${kind}`;
  elements.statusTitle.textContent = title;
  elements.statusMessage.textContent = message;
}

function saveConfig() {
  const payload = {
    apiBase: elements.apiBase.value.trim(),
    apiKey: elements.apiKey.value.trim(),
    apiModel: elements.apiModel.value.trim(),
  };
  localStorage.setItem("media-tool-config", JSON.stringify(payload));
}

function restoreConfig() {
  const raw = localStorage.getItem("media-tool-config");
  const defaults = {
    apiBase: "https://api.openai.com/v1",
    apiKey: "",
    apiModel: "gpt-4o-mini-transcribe",
  };

  if (!raw) {
    elements.apiBase.value = defaults.apiBase;
    elements.apiKey.value = defaults.apiKey;
    elements.apiModel.value = defaults.apiModel;
    return;
  }

  try {
    const parsed = JSON.parse(raw);
    elements.apiBase.value = parsed.apiBase || defaults.apiBase;
    elements.apiKey.value = parsed.apiKey || defaults.apiKey;
    elements.apiModel.value = parsed.apiModel || defaults.apiModel;
  } catch {
    elements.apiBase.value = defaults.apiBase;
    elements.apiKey.value = defaults.apiKey;
    elements.apiModel.value = defaults.apiModel;
  }
}

function getCommonPayload() {
  saveConfig();
  return {
    text: elements.text.value.trim(),
    api_base: elements.apiBase.value.trim(),
    api_key: elements.apiKey.value.trim(),
    model: elements.apiModel.value.trim(),
    save_video: elements.saveVideo.checked,
    save_cover: elements.saveCover.checked,
    save_images: elements.saveImages.checked,
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
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    throw new Error(data.detail || "请求失败");
  }
  return data;
}

function renderSummary(media, meta = {}) {
  elements.resultSummary.innerHTML = "";
  const entries = [
    ["平台", media.platform || "-"],
    ["标题", media.title || "-"],
    ["视频 ID", media.video_id || "-"],
    ["内容类型", media.is_image_post ? "图集" : "视频"],
  ];

  if (meta.output_dir) {
    entries.push(["输出目录", meta.output_dir]);
  }
  if (meta.model) {
    entries.push(["转写模型", meta.model]);
  }
  if (media.author?.nickname) {
    entries.push(["作者", media.author.nickname]);
  }

  for (const [key, value] of entries) {
    const fragment = elements.summaryTemplate.content.cloneNode(true);
    fragment.querySelector(".summary-key").textContent = key;
    fragment.querySelector(".summary-value").textContent = value || "-";
    elements.resultSummary.appendChild(fragment);
  }
}

function looksLikeUrl(value) {
  return /^https?:\/\//i.test(value);
}

function addLinkCard(type, value) {
  if (!value || (Array.isArray(value) && !value.length)) {
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => addLinkCard(`${type} ${index + 1}`, item));
    return;
  }

  const fragment = elements.linkTemplate.content.cloneNode(true);
  fragment.querySelector(".link-type").textContent = type;
  fragment.querySelector(".link-url").textContent = value;

  const open = fragment.querySelector(".link-open");
  if (looksLikeUrl(value)) {
    open.href = value;
    open.textContent = "打开链接";
  } else {
    open.removeAttribute("href");
    open.textContent = "本地路径";
    open.setAttribute("aria-disabled", "true");
  }

  const copyButton = fragment.querySelector(".link-copy");
  copyButton.addEventListener("click", async () => {
    await navigator.clipboard.writeText(value);
    copyButton.textContent = "已复制";
    setTimeout(() => {
      copyButton.textContent = "复制";
    }, 1200);
  });

  elements.linkGrid.appendChild(fragment);
}

function renderLinksFromMedia(media, extra = {}) {
  elements.linkGrid.innerHTML = "";
  addLinkCard("视频地址", media.video_url);
  addLinkCard("音频地址", media.audio_url);
  addLinkCard("封面地址", media.cover_url);
  addLinkCard("图集地址", media.image_list || []);

  if (extra.saved_files) {
    addLinkCard("已保存视频", extra.saved_files.video);
    addLinkCard("已保存封面", extra.saved_files.cover);
    addLinkCard("已保存图集", extra.saved_files.images || []);
    addLinkCard("已保存转写", extra.saved_files.transcript);
  }
}

function clearResults() {
  state.lastParse = null;
  state.lastTranscript = "";
  elements.resultSummary.className = "summary-grid empty-state";
  elements.resultSummary.innerHTML = "<p>暂无结果</p>";
  elements.linkGrid.innerHTML = "";
  elements.transcriptOutput.textContent = "暂无转写内容";
  setStatus("idle", "等待操作", "输入链接后，可以先解析媒体信息，再决定是否下载资源或调用大模型提取文案。");
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (response.ok && data.success) {
      elements.healthStatus.textContent = "在线";
      elements.healthHint.textContent = "服务接口可正常访问";
      return;
    }
    throw new Error("健康检查失败");
  } catch {
    elements.healthStatus.textContent = "异常";
    elements.healthHint.textContent = "无法连接到后端接口";
  }
}

async function handleParse() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先输入分享文案或链接。");
    return;
  }

  setStatus("loading", "正在解析", "正在调用 /api/parse 获取媒体信息。");
  try {
    const result = await requestJson("/api/parse", { text: payload.text });
    state.lastParse = result.data;
    elements.resultSummary.className = "summary-grid";
    renderSummary(result.data);
    renderLinksFromMedia(result.data);
    setStatus("success", "解析完成", "已成功获取平台、标题和资源地址。");
  } catch (error) {
    setStatus("error", "解析失败", error.message);
  }
}

async function handleDownload() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先输入分享文案或链接。");
    return;
  }

  setStatus("loading", "正在下载", "正在调用 /api/download 下载资源。");
  try {
    const result = await requestJson("/api/download", {
      text: payload.text,
      save_video: payload.save_video,
      save_cover: payload.save_cover,
      save_images: payload.save_images,
    });
    state.lastParse = result.data.media;
    elements.resultSummary.className = "summary-grid";
    renderSummary(result.data.media, { output_dir: result.data.output_dir });
    renderLinksFromMedia(result.data.media, { saved_files: result.data.saved_files });
    setStatus("success", "下载完成", `资源已保存到 ${result.data.output_dir}`);
  } catch (error) {
    setStatus("error", "下载失败", error.message);
  }
}

async function handleExtract() {
  const payload = getCommonPayload();
  if (!payload.text) {
    setStatus("error", "缺少输入", "请先输入分享文案或链接。");
    return;
  }

  setStatus("loading", "正在提取文案", "正在调用 /api/extract 下载媒体、抽取音频并提交转写。");
  try {
    const result = await requestJson("/api/extract", payload);
    state.lastParse = result.data.media;
    state.lastTranscript = result.data.transcript || "";
    elements.resultSummary.className = "summary-grid";
    renderSummary(result.data.media, {
      output_dir: result.data.output_dir,
      model: result.data.transcription?.model,
    });
    renderLinksFromMedia(result.data.media, { saved_files: result.data.saved_files });
    elements.transcriptOutput.textContent = state.lastTranscript || "转写接口未返回内容";
    setStatus("success", "提取完成", "文案提取已完成，结果已展示在下方区域。");
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
  elements.downloadAction.addEventListener("click", handleDownload);
  elements.extractAction.addEventListener("click", handleExtract);
  elements.clearResults.addEventListener("click", clearResults);
  elements.copyTranscript.addEventListener("click", copyTranscript);
  elements.fillDemo.addEventListener("click", () => {
    elements.text.value = "https://www.douyin.com/video/7396822576074460467";
    setStatus("idle", "已填充示例", "现在可以直接点击解析链接或下载资源。");
  });
  [elements.apiBase, elements.apiKey, elements.apiModel].forEach((input) => {
    input.addEventListener("change", saveConfig);
  });
}

restoreConfig();
bindEvents();
checkHealth();
clearResults();
