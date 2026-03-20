import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from media_tool_core.schemas import ExtractRequest
from media_tool_core.services.media_service import extract_transcript


class JobNotFoundError(Exception):
    pass


@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: str
    updated_at: str
    logs: list[str] = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "logs": list(self.logs),
            "result": self.result,
            "error": self.error,
        }


MAX_JOB_LOGS = int(os.getenv("MEDIA_TOOL_JOB_MAX_LOGS", "120"))
MAX_JOB_WORKERS = int(os.getenv("MEDIA_TOOL_JOB_WORKERS", "2"))

_executor = ThreadPoolExecutor(max_workers=MAX_JOB_WORKERS, thread_name_prefix="media-tool-job")
_jobs: dict[str, JobRecord] = {}
_jobs_lock = threading.Lock()


def create_extract_job(payload: ExtractRequest) -> dict:
    now = _utc_now()
    job_id = uuid.uuid4().hex
    record = JobRecord(
        job_id=job_id,
        status="queued",
        created_at=now,
        updated_at=now,
        logs=[_format_log("任务已创建，等待执行。")],
    )
    with _jobs_lock:
        _jobs[job_id] = record

    job_payload = payload.model_copy(deep=True)
    _executor.submit(_run_extract_job, job_id, job_payload)
    return record.to_dict()


def get_job(job_id: str) -> dict:
    with _jobs_lock:
        record = _jobs.get(job_id)
        if record is None:
            raise JobNotFoundError(f"未找到任务: {job_id}")
        return record.to_dict()


def _run_extract_job(job_id: str, payload: ExtractRequest) -> None:
    _update_job(job_id, status="running")
    _append_log(job_id, "开始执行转写任务。")

    def progress(message: str) -> None:
        _append_log(job_id, message)

    try:
        result = extract_transcript(payload, progress_callback=progress)
        _update_job(job_id, status="succeeded", result=result)
        _append_log(job_id, "任务执行完成。")
    except Exception as exc:
        _update_job(job_id, status="failed", error=str(exc))
        _append_log(job_id, f"任务失败：{exc}")


def _append_log(job_id: str, message: str) -> None:
    with _jobs_lock:
        record = _jobs.get(job_id)
        if record is None:
            return
        record.logs.append(_format_log(message))
        if len(record.logs) > MAX_JOB_LOGS:
            record.logs[:] = record.logs[-MAX_JOB_LOGS:]
        record.updated_at = _utc_now()


def _update_job(
    job_id: str,
    status: Optional[str] = None,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    with _jobs_lock:
        record = _jobs.get(job_id)
        if record is None:
            return
        if status is not None:
            record.status = status
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
        record.updated_at = _utc_now()


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _format_log(message: str) -> str:
    return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
