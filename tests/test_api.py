from __future__ import annotations

import time

from fastapi.testclient import TestClient
from PIL import Image

from universal_dataset_builder.api.app import create_app
from universal_dataset_builder.core.config import ConfigStore


def _wait_for_job(client: TestClient, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "cancelled", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not finish within {timeout} seconds")


def test_health_and_project_lifecycle(tmp_path):
    config = ConfigStore(tmp_path / "config.json")
    with TestClient(create_app(config_store=config), base_url="http://127.0.0.1") as client:
        blocked_origin = client.get(
            "/api/v1/health",
            headers={"Origin": "http://example.invalid"},
        )
        assert blocked_origin.status_code == 403

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        missing = client.get("/api/v1/project")
        assert missing.status_code == 409

        created = client.post(
            "/api/v1/project/create",
            json={"directory": str(tmp_path), "name": "API project"},
        )
        assert created.status_code == 201
        project = created.json()
        assert project["name"] == "API project"
        assert (tmp_path / "API project" / "project.fdb").is_file()
        assert project["statistics"]["images"] == 0

        closed = client.delete("/api/v1/project")
        assert closed.status_code == 204
        assert client.get("/api/v1/project").status_code == 409

        opened = client.post(
            "/api/v1/project/open",
            json={"database_path": project["database_path"]},
        )
        assert opened.status_code == 200
        assert opened.json()["name"] == "API project"


def test_scan_normalize_gallery_caption_and_file_routes(tmp_path):
    with TestClient(
        create_app(config_store=ConfigStore(tmp_path / "config.json")),
        base_url="http://127.0.0.1",
    ) as client:
        created = client.post(
            "/api/v1/project/create",
            json={"directory": str(tmp_path), "name": "Dataset API"},
        )
        assert created.status_code == 201
        project = created.json()
        source = tmp_path / "Dataset API" / "source"
        Image.new("RGB", (32, 20), "navy").save(source / "wolf.png")

        scan_response = client.post("/api/v1/project/scan", json={"recursive": True})
        assert scan_response.status_code == 202
        scan = _wait_for_job(client, scan_response.json()["job_id"])
        assert scan["status"] == "completed"
        assert scan["result"]["added"] == 1

        images_response = client.get("/api/v1/project/images")
        assert images_response.status_code == 200
        images = images_response.json()
        assert images["total"] == 1
        image = images["items"][0]
        assert image["filename"] == "wolf.png"
        assert "original_path" not in image

        file_response = client.get(image["file_url"])
        assert file_response.status_code == 200
        assert file_response.headers["content-type"].startswith("image/png")

        normalize_response = client.post(
            "/api/v1/project/normalize",
            json={
                "start_number": 1,
                "alpha_mode": "preserve",
                "skip_duplicates": True,
                "sort_mode": "filename_asc",
            },
        )
        assert normalize_response.status_code == 202
        normalized = _wait_for_job(client, normalize_response.json()["job_id"])
        assert normalized["status"] == "completed"
        assert normalized["result"]["normalized"] == 1

        image = client.get("/api/v1/project/images").json()["items"][0]
        caption_response = client.patch(
            f"/api/v1/project/images/{image['image_id']}/caption",
            json={"caption": "A gray wolf in a studio portrait."},
        )
        assert caption_response.status_code == 200
        assert caption_response.json()["metadata_warning"] is None

        image = client.get("/api/v1/project/images").json()["items"][0]
        assert image["status"] == "Reviewed"
        assert image["caption_reviewed"] is True

        status_response = client.patch(
            f"/api/v1/project/images/{image['image_id']}/status",
            json={"status": "Excluded"},
        )
        assert status_response.status_code == 200
        assert status_response.json()["metadata_warning"] is None
        assert (tmp_path / "Dataset API" / "dataset" / "metadata.jsonl").read_text(
            encoding="utf-8"
        ) == ""


def test_settings_never_return_saved_api_key(tmp_path):
    config = ConfigStore(tmp_path / "config.json")
    with TestClient(create_app(config_store=config), base_url="http://127.0.0.1") as client:
        updated = client.put(
            "/api/v1/settings",
            json={
                "theme": "light",
                "vlm_base_url": "http://127.0.0.1:8080/v1",
                "vlm_api_key": "a-secret-key",
                "vlm_timeout": 180,
                "caption_prompt": "Describe visible details.",
            },
        )
        assert updated.status_code == 200
        payload = updated.json()
        assert payload["vlm_api_key_configured"] is True
        assert "vlm_api_key" not in payload
        assert "a-secret-key" not in updated.text

        stored = client.get("/api/v1/settings")
        assert stored.status_code == 200
        assert stored.json()["theme"] == "light"
        assert stored.json()["vlm_timeout"] == 180
        assert "a-secret-key" not in stored.text


def test_websocket_delivers_terminal_job_state(tmp_path):
    with TestClient(
        create_app(config_store=ConfigStore(tmp_path / "config.json")),
        base_url="http://127.0.0.1",
    ) as client:
        client.post(
            "/api/v1/project/create",
            json={"directory": str(tmp_path), "name": "WebSocket API"},
        )
        response = client.post("/api/v1/project/scan", json={})
        job_id = response.json()["job_id"]
        final = _wait_for_job(client, job_id)

        with client.websocket_connect(
            f"/api/v1/ws/jobs/{job_id}",
            headers={"host": "127.0.0.1"},
        ) as websocket:
            message = websocket.receive_json()
        assert message["status"] == "completed"
        assert message["job_id"] == job_id
        assert final["status"] == "completed"


def test_invalid_project_and_image_payloads_are_rejected(tmp_path):
    with TestClient(
        create_app(config_store=ConfigStore(tmp_path / "config.json")),
        base_url="http://127.0.0.1",
    ) as client:
        invalid_open = client.post(
            "/api/v1/project/open",
            json={"database_path": str(tmp_path / "bad.fdb")},
        )
        assert invalid_open.status_code == 400
        assert client.post(
            "/api/v1/project/create",
            json={"directory": str(tmp_path), "name": "Invalid API"},
        ).status_code == 201
        assert client.patch(
            "/api/v1/project/images/1/status",
            json={"status": "Not a status"},
        ).status_code == 422
