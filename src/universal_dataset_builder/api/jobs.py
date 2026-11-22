"""Single-runner background job management for the local API."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from threading import Event, RLock
from typing import Callable
from uuid import uuid4

LOGGER = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]
JobOperation = Callable[[Callable[[], bool], ProgressCallback], object]

_ACTIVE_STATES = frozenset({"queued", "running", "cancelling"})
_TERMINAL_STATES = frozenset({"completed", "cancelled", "failed"})


class ActiveJobError(RuntimeError):
    """Raised when another mutating job is already active."""


class JobNotCancellableError(RuntimeError):
    """Raised when a caller tries to cancel an operation that cannot be stopped."""


@dataclass(slots=True)
class _Job:
    job_id: str
    kind: str
    status: str
    cancellable: bool
    cancel_event: Event
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress_current: int = 0
    progress_total: int = 0
    current_item: str = ""
    result: object | None = None
    error: str | None = None


def _json_value(value: object) -> object:
    """Convert dataclasses and nested containers to JSON-compatible values."""
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JobManager:
    """Serialize mutating operations and expose progress for polling or WebSockets."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: dict[str, _Job] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="udb-api-job",
        )
        self._closed = False

    @contextmanager
    def mutation_guard(self):
        """Protect synchronous mutations from overlapping background jobs."""
        with self._lock:
            if self._closed:
                raise RuntimeError("The API job manager is shutting down.")
            if any(job.status in _ACTIVE_STATES for job in self._jobs.values()):
                raise ActiveJobError("Another dataset operation is already running.")
            yield

    def submit(
        self,
        kind: str,
        operation: JobOperation,
        *,
        cancellable: bool = True,
    ) -> dict[str, object]:
        """Queue one operation, rejecting overlapping mutations."""
        with self._lock:
            if self._closed:
                raise RuntimeError("The API job manager is shutting down.")
            if any(job.status in _ACTIVE_STATES for job in self._jobs.values()):
                raise ActiveJobError("Another dataset operation is already running.")

            job_id = uuid4().hex
            job = _Job(
                job_id=job_id,
                kind=kind,
                status="queued",
                cancellable=cancellable,
                cancel_event=Event(),
                created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
            self._jobs[job_id] = job
            self._executor.submit(self._execute, job_id, operation)
            return self._snapshot(job)

    def _execute(self, job_id: str, operation: JobOperation) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now(UTC).isoformat(timespec="seconds")

        def report_progress(current: int, total: int, item: str = "") -> None:
            with self._lock:
                current_job = self._jobs.get(job_id)
                if current_job is None:
                    return
                current_job.progress_current = max(0, int(current))
                current_job.progress_total = max(0, int(total))
                current_job.current_item = str(item)

        try:
            result = operation(job.cancel_event.is_set, report_progress)
        except Exception as error:
            LOGGER.exception("API job %s (%s) failed", job_id, job.kind)
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = str(error)
                job.finished_at = datetime.now(UTC).isoformat(timespec="seconds")
        else:
            was_cancelled = bool(getattr(result, "cancelled", False))
            with self._lock:
                job = self._jobs[job_id]
                job.result = _json_value(result)
                job.status = "cancelled" if was_cancelled else "completed"
                job.finished_at = datetime.now(UTC).isoformat(timespec="seconds")

    def get(self, job_id: str) -> dict[str, object] | None:
        """Return a serializable snapshot of one job."""
        with self._lock:
            job = self._jobs.get(job_id)
            return self._snapshot(job) if job is not None else None

    def cancel(self, job_id: str) -> dict[str, object] | None:
        """Request cancellation of a cancellable queued or running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in _TERMINAL_STATES:
                return self._snapshot(job)
            if not job.cancellable:
                raise JobNotCancellableError(
                    f"The {job.kind} operation does not support cancellation."
                )
            job.cancel_event.set()
            job.status = "cancelling"
            return self._snapshot(job)

    @staticmethod
    def _snapshot(job: _Job) -> dict[str, object]:
        percent = (
            round(job.progress_current / job.progress_total * 100)
            if job.progress_total > 0
            else 0
        )
        return {
            "job_id": job.job_id,
            "kind": job.kind,
            "status": job.status,
            "cancellable": job.cancellable,
            "progress": {
                "current": job.progress_current,
                "total": job.progress_total,
                "percent": min(100, max(0, percent)),
                "item": job.current_item,
            },
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "result": job.result,
            "error": job.error,
        }

    def shutdown(self) -> None:
        """Stop accepting jobs and release the worker thread."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for job in self._jobs.values():
                if job.cancellable and job.status in _ACTIVE_STATES:
                    job.cancel_event.set()
        self._executor.shutdown(wait=True, cancel_futures=True)
