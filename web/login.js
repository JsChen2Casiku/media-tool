const loginElements = {
  form: document.querySelector("#login-form"),
  username: document.querySelector("#login-username"),
  password: document.querySelector("#login-password"),
  submit: document.querySelector("#login-submit"),
  message: document.querySelector("#login-message"),
};

function getStoredTheme() {
  const directTheme = localStorage.getItem("media-tool-theme");
  if (directTheme) {
    return directTheme;
  }

  try {
    const storedConfig = JSON.parse(localStorage.getItem("media-tool-config") || "{}");
    if (typeof storedConfig.theme === "string" && storedConfig.theme.trim()) {
      return storedConfig.theme.trim();
    }
  } catch {
    return "system";
  }

  return "system";
}

function getResolvedTheme(theme) {
  if (theme !== "system") {
    return theme;
  }
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyLoginTheme() {
  const resolvedTheme = getResolvedTheme(getStoredTheme());
  document.body.classList.toggle("theme-dark", resolvedTheme === "dark");
}

function setLoginMessage(message, kind = "default") {
  if (!(loginElements.message instanceof HTMLElement)) {
    return;
  }
  loginElements.message.textContent = message;
  loginElements.message.dataset.kind = kind;
}

async function submitLogin(event) {
  event.preventDefault();
  if (!(loginElements.username instanceof HTMLInputElement) || !(loginElements.password instanceof HTMLInputElement)) {
    return;
  }

  const username = loginElements.username.value.trim();
  const password = loginElements.password.value;
  if (!username || !password) {
    setLoginMessage("请输入账号和密码。", "error");
    return;
  }

  if (loginElements.submit instanceof HTMLButtonElement) {
    loginElements.submit.disabled = true;
  }
  setLoginMessage("正在验证登录信息。", "loading");

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const raw = await response.text();
    const payload = raw ? JSON.parse(raw) : {};
    if (!response.ok) {
      throw new Error(payload.detail || payload.message || "登录失败。");
    }
    setLoginMessage("登录成功，正在进入系统。", "success");
    window.location.href = "/";
  } catch (error) {
    setLoginMessage(error instanceof Error ? error.message : String(error), "error");
  } finally {
    if (loginElements.submit instanceof HTMLButtonElement) {
      loginElements.submit.disabled = false;
    }
  }
}

function bindThemeSync() {
  if (!window.matchMedia) {
    return;
  }
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", () => {
    if (getStoredTheme() === "system") {
      applyLoginTheme();
    }
  });
}

function initLogin() {
  applyLoginTheme();
  bindThemeSync();

  if (loginElements.form instanceof HTMLFormElement) {
    loginElements.form.addEventListener("submit", (event) => {
      void submitLogin(event);
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLogin);
} else {
  initLogin();
}
