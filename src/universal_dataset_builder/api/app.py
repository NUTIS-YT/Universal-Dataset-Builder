"""FastAPI application exposing shared UDB services to local front ends."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from universal_dataset_builder import __version__
from universal_dataset_builder.api.jobs import (
    ActiveJobError,
    JobManager,
    JobNotCancellableError,
)
from universal_dataset_builder.api.schemas import (
    CaptionGenerationRequest,
    CaptionUpdateRequest,
    ImageStatusUpdateRequest,
    NormalizeRequest,
    ProjectCreateRequest,
    ProjectOpenRequest,
    ScanRequest,
    SettingsUpdateRequest,
    VLMTestRequest,
)
from universal_dataset_builder.core.config import ConfigStore
from universal_dataset_builder.core.project import Project
from universal_dataset_builder.services.caption_service import CaptionGenerationService
from universal_dataset_builder.services.dataset_service import DatasetService
from universal_dataset_builder.services.project_service import ProjectService
from universal_dataset_builder.vlm.client import (
    OpenAICompatibleClient,
    VLMError,
    normalize_api_base_url,
)

LOGGER = logging.getLogger(__name__)


def _project_payload(project: Project) -> dict[str, object]:
    return {
        "name": project.name,
        "database_path": str(project.path),
        "root_path": str(project.path.parent),
        "source_path": str(project.source_path),
        "dataset_path": str(project.dataset_path),
        "metadata_path": str(project.metadata_path),
        "metadata_format": project.metadata_format,
        "statistics": ProjectService.statistics(project),
    }


def _public_settings(config: ConfigStore) -> dict[str, object]:
    return {
        "theme": config.get("theme", "dark"),
        "vlm_base_url": config.get("vlm_base_url", ""),
        "vlm_api_key_configured": bool(config.get("vlm_api_key", "")),
        "vlm_timeout": config.get("vlm_timeout", 120),
        "vlm_model": config.get("vlm_model", ""),
        "vlm_models": config.get("vlm_models", []),
        "caption_prompt": config.get("caption_prompt", ""),
    }


def _public_image(row: dict[str, object]) -> dict[str, object]:
    return {
        "image_id": int(row["image_id"]),
        "filename": str(row["filename"]),
        "original_filename": str(row["original_filename"]),
        "width": row.get("width"),
        "height": row.get("height"),
        "format": row.get("format"),
        "status": str(row["status"]),
        "caption_text": str(row.get("caption_text") or ""),
        "caption_reviewed": bool(row.get("caption_reviewed")),
        "file_url": f"/api/v1/project/images/{int(row['image_id'])}/file",
    }


def create_app(
    *,
    config_store: ConfigStore | None = None,
    job_manager: JobManager | None = None,
) -> FastAPI:
    """Create an isolated API app; the default server binds only to loopback."""
    config = config_store or ConfigStore()
    jobs = job_manager or JobManager()
    project_lock = RLock()
    active_project: Project | None = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        jobs.shutdown()

    app = FastAPI(
        title="Universal Dataset Builder API",
        version=__version__,
        description="Local API shared by the Legacy and Expressive desktop interfaces.",
        lifespan=lifespan,
    )
    app.state.config_store = config
    app.state.job_manager = jobs
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "::1"],
    )

    def require_project() -> Project:
        with project_lock:
            if active_project is None:
                raise HTTPException(status_code=409, detail="No project is currently open.")
            return active_project

    @contextmanager
    def mutation_guard():
        try:
            with jobs.mutation_guard():
                yield
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    def submit_job(kind: str, operation, *, cancellable: bool = True):
        try:
            return jobs.submit(kind, operation, cancellable=cancellable)
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.middleware("http")
    async def reject_cross_origin_requests(request, call_next):
        origin = request.headers.get("origin")
        if origin:
            parsed_origin = urlsplit(origin)
            request_host = request.headers.get("host", "").casefold()
            if parsed_origin.scheme != "http" or parsed_origin.netloc.casefold() != request_host:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin requests are not allowed."},
                )
        return await call_next(request)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "name": "Universal Dataset Builder", "version": __version__}

    @app.get("/api/v1/project")
    def get_project() -> dict[str, object]:
        project = require_project()
        return _project_payload(project)

    @app.post("/api/v1/project/create", status_code=201)
    def create_project(payload: ProjectCreateRequest) -> dict[str, object]:
        nonlocal active_project
        if (
            payload.name in {".", ".."}
            or "/" in payload.name
            or "\\" in payload.name
        ):
            raise HTTPException(status_code=422, detail="Project name must be a single folder name.")
        try:
            with mutation_guard():
                project_directory = Path(payload.directory).expanduser() / payload.name
                project = ProjectService.create(
                    project_directory,
                    payload.name,
                    metadata_format=payload.metadata_format,
                )
                with project_lock:
                    active_project = project
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return _project_payload(project)

    @app.post("/api/v1/project/open")
    def open_project(payload: ProjectOpenRequest) -> dict[str, object]:
        nonlocal active_project
        try:
            with mutation_guard():
                project = ProjectService.open(Path(payload.database_path).expanduser())
                with project_lock:
                    active_project = project
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return _project_payload(project)

    @app.delete("/api/v1/project", status_code=204, response_class=Response)
    def close_project() -> Response:
        nonlocal active_project
        try:
            with mutation_guard():
                with project_lock:
                    active_project = None
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return Response(status_code=204)

    @app.get("/api/v1/project/statistics")
    def project_statistics() -> dict[str, int]:
        return ProjectService.statistics(require_project())

    @app.get("/api/v1/project/images")
    def list_project_images(
        search: str = Query(default="", max_length=512),
        status: str | None = Query(default=None, max_length=32),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, object]:
        project = require_project()
        if status is not None and status not in DatasetService.statuses:
            raise HTTPException(status_code=400, detail="Unsupported image status.")
        try:
            rows = DatasetService.list_images(project.path)
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        clean_search = search.strip().casefold()
        filtered = [
            row for row in rows
            if (not clean_search or clean_search in str(row["filename"]).casefold())
            and (status is None or row["status"] == status)
        ]
        return {
            "items": [_public_image(row) for row in filtered[offset:offset + limit]],
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
        }

    def get_image(project: Project, image_id: int) -> dict[str, object]:
        for row in DatasetService.list_images(project.path):
            if int(row["image_id"]) == image_id:
                return row
        raise HTTPException(status_code=404, detail="Image record not found.")

    @app.get("/api/v1/project/images/{image_id}/file")
    def get_image_file(image_id: int):
        project = require_project()
        image = get_image(project, image_id)
        candidates: list[tuple[Path, Path]] = []
        if image.get("normalized_path"):
            candidates.append((Path(str(image["normalized_path"])), project.dataset_path))
        candidates.append((Path(str(image["original_path"])), project.source_path))

        for candidate, root in candidates:
            resolved = candidate.expanduser().resolve()
            resolved_root = root.expanduser().resolve()
            try:
                resolved.relative_to(resolved_root)
            except ValueError:
                continue
            if resolved.is_file():
                media_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
                return FileResponse(resolved, media_type=media_type, filename=resolved.name)
        raise HTTPException(status_code=404, detail="Image file is missing from the project.")

    @app.patch("/api/v1/project/images/{image_id}/caption")
    def update_caption(
        image_id: int,
        payload: CaptionUpdateRequest,
    ) -> dict[str, object]:
        try:
            with mutation_guard():
                project = require_project()
                warning = DatasetService.save_caption(
                    project.path,
                    project.dataset_path,
                    image_id,
                    payload.caption,
                )
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "saved": True,
            "metadata_warning": warning,
            "statistics": ProjectService.statistics(project),
        }

    @app.patch("/api/v1/project/images/{image_id}/status")
    def update_image_status(
        image_id: int,
        payload: ImageStatusUpdateRequest,
    ) -> dict[str, object]:
        try:
            with mutation_guard():
                project = require_project()
                warning = DatasetService.set_status(
                    project.path,
                    project.dataset_path,
                    image_id,
                    payload.status,
                )
        except ActiveJobError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "updated": True,
            "status": payload.status,
            "metadata_warning": warning,
            "statistics": ProjectService.statistics(project),
        }

    @app.post("/api/v1/project/scan", status_code=202)
    def start_scan(payload: ScanRequest):
        with mutation_guard():
            project = require_project()

            def operation(cancel_requested, progress):
                return DatasetService.scan_source(
                    project.path,
                    project.source_path,
                    recursive=payload.recursive,
                    progress_callback=lambda current, total: progress(current, total, ""),
                    cancel_requested=cancel_requested,
                )

            return submit_job("scan", operation)

    @app.post("/api/v1/project/normalize", status_code=202)
    def start_normalization(payload: NormalizeRequest):
        with mutation_guard():
            project = require_project()

            def operation(cancel_requested, progress):
                return DatasetService.normalize_images(
                    project.path,
                    project.source_path,
                    project.dataset_path,
                    start_number=payload.start_number,
                    alpha_mode=payload.alpha_mode,
                    skip_duplicates=payload.skip_duplicates,
                    sort_mode=payload.sort_mode,
                    progress_callback=progress,
                    cancel_requested=cancel_requested,
                )

            return submit_job("normalization", operation)

    @app.post("/api/v1/project/captions/generate", status_code=202)
    def start_caption_generation(payload: CaptionGenerationRequest):
        with mutation_guard():
            project = require_project()
            settings = config.values
            model = (payload.model or str(settings.get("vlm_model", ""))).strip()
            prompt = payload.prompt if payload.prompt is not None else str(
                settings.get("caption_prompt", "")
            )
            if not model:
                raise HTTPException(
                    status_code=400,
                    detail="Select a VLM model in VLM Connection before generating captions.",
                )
            base_url = str(settings.get("vlm_base_url", ""))
            api_key = str(settings.get("vlm_api_key", ""))
            timeout_seconds = int(settings.get("vlm_timeout", 120))

            def operation(cancel_requested, progress):
                return CaptionGenerationService.generate(
                    project.path,
                    project.source_path,
                    project.dataset_path,
                    base_url=base_url,
                    api_key=api_key,
                    timeout_seconds=timeout_seconds,
                    model=model,
                    prompt=prompt,
                    selection_mode=payload.selection_mode,
                    limit=payload.limit,
                    cancel_requested=cancel_requested,
                    progress_callback=progress,
                )

            return submit_job("caption_generation", operation)

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job

    @app.delete("/api/v1/jobs/{job_id}")
    def cancel_job(job_id: str) -> dict[str, object]:
        try:
            job = jobs.cancel(job_id)
        except JobNotCancellableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job

    @app.websocket("/api/v1/ws/jobs/{job_id}")
    async def watch_job(websocket: WebSocket, job_id: str) -> None:
        origin = websocket.headers.get("origin")
        request_host = websocket.headers.get("host", "").casefold()
        if origin:
            parsed_origin = urlsplit(origin)
            if parsed_origin.scheme != "http" or parsed_origin.netloc.casefold() != request_host:
                await websocket.close(code=4403)
                return
        await websocket.accept()
        try:
            while True:
                job = jobs.get(job_id)
                if job is None:
                    await websocket.send_json({"error": "Job not found."})
                    await websocket.close(code=4404)
                    return
                await websocket.send_json(job)
                if job["status"] in {"completed", "cancelled", "failed"}:
                    return
                await asyncio.sleep(0.25)
        except WebSocketDisconnect:
            return

    @app.get("/api/v1/settings")
    def get_settings() -> dict[str, object]:
        return _public_settings(config)

    @app.put("/api/v1/settings")
    def update_settings(payload: SettingsUpdateRequest) -> dict[str, object]:
        fields = payload.model_fields_set
        try:
            for field in fields:
                value = getattr(payload, field)
                if field == "vlm_api_key":
                    config.set(field, value if value is not None else "")
                elif value is not None:
                    config.set(field, value)
            config.save()
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return _public_settings(config)

    @app.post("/api/v1/vlm/test")
    def test_vlm_connection(payload: VLMTestRequest) -> dict[str, object]:
        try:
            normalized_url = normalize_api_base_url(payload.base_url)
            with OpenAICompatibleClient(
                normalized_url,
                api_key=payload.api_key,
                timeout_seconds=payload.timeout_seconds,
            ) as client:
                models = client.list_models()
        except (VLMError, OSError, ValueError) as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        previous_model = str(config.get("vlm_model", ""))
        selected_model = previous_model if previous_model in models else (
            models[0] if models else ""
        )
        try:
            config.set("vlm_base_url", normalized_url)
            config.set("vlm_api_key", payload.api_key)
            config.set("vlm_timeout", payload.timeout_seconds)
            config.set("vlm_models", models)
            config.set("vlm_model", selected_model)
            config.save()
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

        return {
            "connected": True,
            "base_url": normalized_url,
            "models": models,
            "selected_model": selected_model,
            "api_key_configured": bool(payload.api_key),
        }

    @app.get("/api/v1/vlm/models")
    def get_vlm_models() -> dict[str, object]:
        settings = config.values
        try:
            with OpenAICompatibleClient(
                str(settings.get("vlm_base_url", "")),
                api_key=str(settings.get("vlm_api_key", "")),
                timeout_seconds=int(settings.get("vlm_timeout", 120)),
            ) as client:
                models = client.list_models()
        except (VLMError, OSError, ValueError) as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        config.set("vlm_models", models)
        config.save()
        return {"models": models, "selected_model": config.get("vlm_model", "")}

    return app

