from __future__ import annotations

import base64
import json

import httpx
import pytest
from PIL import Image

from universal_dataset_builder.vlm.client import (
    OpenAICompatibleClient,
    VLMError,
    image_to_data_url,
    normalize_api_base_url,
)


def test_normalize_api_base_url_adds_v1_and_rejects_invalid_urls():
    assert normalize_api_base_url("http://localhost:8080") == "http://localhost:8080/v1"
    assert normalize_api_base_url("http://localhost:8080/v1/") == "http://localhost:8080/v1"
    assert normalize_api_base_url("https://example.test/custom/v1") == (
        "https://example.test/custom/v1"
    )
    with pytest.raises(VLMError):
        normalize_api_base_url("file:///tmp/api")
    with pytest.raises(VLMError):
        normalize_api_base_url("http://user:password@example.test/v1")


def test_list_models_uses_optional_bearer_authentication():
    observed = {}

    def handler(request):
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": "z-model", "object": "model"},
                    {"id": "a-model", "object": "model"},
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    with OpenAICompatibleClient(
        "http://localhost:8080/v1",
        api_key="local-secret",
        transport=transport,
    ) as client:
        models = client.list_models()

    assert models == ["a-model", "z-model"]
    assert observed["url"] == "http://localhost:8080/v1/models"
    assert observed["authorization"] == "Bearer local-secret"


def test_caption_image_sends_data_url_prompt_and_model(tmp_path):
    source = tmp_path / "sample.png"
    Image.new("RGB", (24, 12), "navy").save(source)
    observed = {}

    def handler(request):
        observed["url"] = str(request.url)
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "  A navy rectangle.  ",
                        }
                    }
                ]
            },
        )

    with OpenAICompatibleClient(
        "http://localhost:8080/v1",
        transport=httpx.MockTransport(handler),
    ) as client:
        caption = client.caption_image(source, "Describe it.", "vision-model")

    assert caption == "A navy rectangle."
    assert observed["url"] == "http://localhost:8080/v1/chat/completions"
    payload = observed["payload"]
    assert payload["model"] == "vision-model"
    assert payload["messages"][1]["content"][0]["text"] == "Describe it."
    image_url = payload["messages"][1]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(image_url.split(",", 1)[1])


def test_image_data_url_preserves_alpha_as_png(tmp_path):
    source = tmp_path / "transparent.png"
    Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(source)

    data_url = image_to_data_url(source)

    assert data_url.startswith("data:image/png;base64,")


def test_api_errors_are_reported_with_server_message():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            401,
            json={"error": {"message": "Invalid API key"}},
        )
    )
    with OpenAICompatibleClient(
        "http://localhost:8080/v1",
        transport=transport,
    ) as client:
        with pytest.raises(VLMError, match="Invalid API key"):
            client.list_models()


def test_completion_text_can_be_extracted_from_content_blocks(tmp_path):
    source = tmp_path / "sample.png"
    Image.new("RGB", (4, 4), "white").save(source)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "A white "},
                                {"type": "text", "text": "square."},
                            ]
                        }
                    }
                ]
            },
        )
    )
    with OpenAICompatibleClient(
        "http://localhost:8080/v1",
        transport=transport,
    ) as client:
        result = client.caption_image(source, "Describe.", "vision-model")
    assert result == "A white \nsquare."
