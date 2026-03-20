import os
import secrets
import threading
import time
from pathlib import Path

from fastapi import HTTPException, Request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
AUTH_CONFIG_PATH = Path(
    os.getenv("MEDIA_TOOL_AUTH_CONFIG_PATH")
    or str(PROJECT_ROOT / "runtime" / "storage" / "auth.env")
).resolve()
SESSION_COOKIE_NAME = "media_tool_session"
SESSION_TTL_SECONDS = int(os.getenv("MEDIA_TOOL_AUTH_SESSION_TTL", "604800"))

_lock = threading.Lock()
_sessions: dict[str, dict[str, float | str]] = {}


def get_auth_username() -> str:
    return str(_auth_state["username"])


def get_cookie_secure() -> bool:
    return (os.getenv("MEDIA_TOOL_AUTH_COOKIE_SECURE") or "false").strip().lower() in {"1", "true", "yes", "on"}


def get_session_max_age() -> int:
    return SESSION_TTL_SECONDS


def validate_login(username: str, password: str) -> None:
    expected_username = get_auth_username()
    expected_password = str(_auth_state["password"])
    if username != expected_username or password != expected_password:
        raise HTTPException(status_code=401, detail="账号或密码错误。")


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + SESSION_TTL_SECONDS
    with _lock:
        _sessions[token] = {"username": username, "expires_at": expires_at}
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _sessions.pop(token, None)


def revoke_all_sessions() -> None:
    with _lock:
        _sessions.clear()


def get_authenticated_user(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    with _lock:
        payload = _sessions.get(token)
        if not payload:
            return None
        expires_at = float(payload["expires_at"])
        if expires_at <= time.time():
            _sessions.pop(token, None)
            return None
        return str(payload["username"])


def require_auth(request: Request) -> str:
    username = get_authenticated_user(request)
    if username:
        return username
    raise HTTPException(status_code=401, detail="未登录或登录状态已失效。")


def update_password(current_password: str, new_password: str, confirm_password: str) -> None:
    if current_password != str(_auth_state["password"]):
        raise ValueError("当前密码不正确。")
    if new_password != confirm_password:
        raise ValueError("两次输入的新密码不一致。")
    if len(new_password.strip()) < 6:
        raise ValueError("新密码至少需要 6 位。")

    _auth_state["password"] = new_password
    os.environ["MEDIA_TOOL_AUTH_PASSWORD"] = new_password
    _write_env_value(AUTH_CONFIG_PATH, "MEDIA_TOOL_AUTH_PASSWORD", new_password)
    if ENV_PATH.exists():
        _write_env_value(ENV_PATH, "MEDIA_TOOL_AUTH_PASSWORD", new_password)
    revoke_all_sessions()


def _resolve_auth_value(key: str, default: str) -> str:
    persisted = _read_env_value(AUTH_CONFIG_PATH, key)
    if persisted is not None:
        return persisted
    runtime_value = (os.getenv(key) or "").strip()
    if runtime_value:
        return runtime_value
    return default


def _read_env_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        current_key, current_value = line.split("=", 1)
        if current_key.strip() != key:
            continue
        return current_value.strip().strip("'\"")
    return None


def _write_env_value(path: Path, key: str, value: str) -> None:
    value_text = str(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    replaced = False
    next_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            next_lines.append(f"{key}={value_text}")
            replaced = True
        else:
            next_lines.append(line)

    if not replaced:
        if next_lines and next_lines[-1].strip():
            next_lines.append("")
        next_lines.append(f"{key}={value_text}")

    path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")


_auth_state = {
    "username": _resolve_auth_value("MEDIA_TOOL_AUTH_USERNAME", "admin"),
    "password": _resolve_auth_value("MEDIA_TOOL_AUTH_PASSWORD", "admin123456"),
}
