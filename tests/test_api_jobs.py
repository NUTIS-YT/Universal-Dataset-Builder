from __future__ import annotations

import threading
import time

import pytest

from universal_dataset_builder.api.jobs import (
    ActiveJobError,
    JobManager,
    JobNotCancellableError,
)


def test_job_manager_reports_progress_and_rejects_overlapping_mutations():
    manager = JobManager()
    started = threading.Event()
    release = threading.Event()

    def operation(cancel_requested, progress):
        started.set()
        progress(1, 2, "first.png")
        release.wait(timeout=2)
        progress(2, 2, "second.png")
        return {"cancelled": cancel_requested()}

    try:
        first = manager.submit("test", operation)
        assert started.wait(timeout=1)
        snapshot = manager.get(first["job_id"])
        assert snapshot is not None
        assert snapshot["progress"]["current"] == 1
        assert snapshot["progress"]["item"] == "first.png"

        with pytest.raises(ActiveJobError):
            manager.submit("second", lambda _cancel, _progress: None)
        with pytest.raises(ActiveJobError):
            with manager.mutation_guard():
                pass
    finally:
        release.set()

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        final = manager.get(first["job_id"])
        if final and final["status"] == "completed":
            break
        time.sleep(0.01)
    assert final is not None
    assert final["status"] == "completed"
    assert final["progress"]["percent"] == 100
    manager.shutdown()


def test_job_manager_cancellation_and_non_cancellable_jobs():
    manager = JobManager()
    started = threading.Event()

    def cancellable_operation(cancel_requested, _progress):
        started.set()
        while not cancel_requested():
            time.sleep(0.005)
        return type("Result", (), {"cancelled": True})()

    try:
        cancellable = manager.submit("normalization", cancellable_operation)
        assert started.wait(timeout=1)
        cancelling = manager.cancel(cancellable["job_id"])
        assert cancelling is not None
        assert cancelling["status"] == "cancelling"

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            result = manager.get(cancellable["job_id"])
            if result and result["status"] == "cancelled":
                break
            time.sleep(0.01)
        assert result is not None
        assert result["status"] == "cancelled"

        non_cancellable = manager.submit(
            "locked-task",
            lambda _cancel, _progress: None,
            cancellable=False,
        )
        with pytest.raises(JobNotCancellableError):
            manager.cancel(non_cancellable["job_id"])
    finally:
        manager.shutdown()
