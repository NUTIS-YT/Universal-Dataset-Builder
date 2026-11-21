"""OpenAI-compatible VLM client for image caption generation."""

from __future__ import annotations

import base64
import io
import warnings
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError


class VLMError(RuntimeError):
    """A readable error returned by the configured VLM endpoint."""


def normalize_api_base_url(value: str) -> str:
    """Validate an API root and append /v1 when the version path is omitted."""
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
        path = parsed.path.rstrip("/")
        if not path.endswith("/v1"):
            path = f"{path}/v1"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    except ValueError as error:
        raise VLMError(
            "Enter a valid HTTP(S) API address, for example http://127.0.0.1:8080/v1."
        ) from error


def image_to_data_url(image_path: Path, *, max_edge: int = 1536) -> str:
    """Encode a resized image as a data URL accepted by vision chat endpoints."""
    path = Path(image_path)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as opened:
                oriented = ImageOps.exif_transpose(opened)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                if has_alpha:
                    image = oriented.convert("RGBA")
                    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    image.save(output, format="PNG", optimize=True)
                    media_type = "image/png"
                else:
                    image = oriented.convert("RGB")
                    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    image.save(output, format="JPEG", quality=88, optimize=True)
                    media_type = "image/jpeg"
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        raise VLMError(f"Cannot prepare image '{path.name}': {error}") from error

    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _extract_text(payload: object) -> str:
    """Extract assistant text from common OpenAI-compatible response shapes."""
    if not isinstance(payload, dict):
        raise VLMError("The VLM returned an invalid JSON response.")

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise VLMError("The VLM response does not contain a completion choice.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise VLMError("The VLM response does not contain a message.")

    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    else:
        text = ""

    result = text.strip()
    if not result:
        raise VLMError("The VLM returned an empty caption.")
    return result


class OpenAICompatibleClient:
    """Small synchronous client; run it from a worker, never from the GUI thread."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        timeout_seconds: int = 120,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = normalize_api_base_url(base_url)
        self._headers = {"Accept": "application/json"}
        if api_key.strip():
            self._headers["Authorization"] = f"Bearer {api_key.strip()}"
        timeout = httpx.Timeout(
            float(timeout_seconds),
            connect=min(float(timeout_seconds), 15.0),
        )
        self._client = httpx.Client(
            timeout=timeout,
            headers=self._headers,
            transport=transport,
        )

    def __enter__(self) -> OpenAICompatibleClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            message = response.text[:600].strip()
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    api_error = payload.get("error")
                    if isinstance(api_error, dict) and isinstance(api_error.get("message"), str):
                        message = api_error["message"][:600]
            except ValueError:
                pass
            if not message:
                message = "The server returned an HTTP error."
            raise VLMError(
                f"VLM API returned HTTP {response.status_code}: {message}"
            ) from error

    def list_models(self) -> list[str]:
        """Fetch model identifiers from GET /models."""
        try:
            response = self._client.get(f"{self.base_url}/models")
        except httpx.RequestError as error:
            raise VLMError(f"Could not reach the VLM API: {error}") from error

        self._raise_api_error(response)
        try:
            payload = response.json()
        except ValueError as error:
            raise VLMError("The VLM /models endpoint returned invalid JSON.") from error

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise VLMError("The VLM /models response does not contain a data list.")

        model_ids = sorted(
            {
                item["id"].strip()
                for item in data
                if isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and item["id"].strip()
            },
            key=str.casefold,
        )
        return model_ids

    def caption_image(self, image_path: Path, prompt: str, model: str) -> str:
        """Send one image and a caption instruction to POST /chat/completions."""
        clean_prompt = prompt.strip()
        clean_model = model.strip()
        if not clean_prompt:
            raise VLMError("Caption prompt cannot be empty.")
        if not clean_model:
            raise VLMError("Select a VLM model before generating captions.")

        image_url = image_to_data_url(image_path)
        payload = {
            "model": clean_model,
            "temperature": 0.2,
            "max_tokens": 512,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an accurate image captioning assistant. "
                        "Describe only visible details and do not invent facts."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": clean_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
        }

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
        except httpx.RequestError as error:
            raise VLMError(f"Could not send the image to the VLM API: {error}") from error

        self._raise_api_error(response)
        try:
            response_payload = response.json()
        except ValueError as error:
            raise VLMError("The VLM completion endpoint returned invalid JSON.") from error
        return _extract_text(response_payload)
