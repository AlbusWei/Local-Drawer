import asyncio

from backend.app import models, services


def test_model_routing_rules(monkeypatch):
    monkeypatch.setattr(services, "EVOLINK_API_KEY", "test-key")
    assert services._is_evolink_model("doubao-seedream-5.0-lite") is True
    assert services._is_evolink_model("gemini-3-pro-image-preview") is False
    assert services._is_evolink_model("gemini-3.1-flash-image-preview") is False
    assert services._is_web_search_supported_on_gemini("gemini-3.1-flash-image-preview") is True
    assert services._is_web_search_supported_on_gemini("gemini-3-pro-image-preview") is False
    assert services._should_fallback_to_evolink("gemini-3.1-flash-image-preview", Exception("upstream error")) is True
    assert services._should_fallback_to_evolink("gemini-3-pro-image-preview", Exception("upstream error")) is True
    assert services._is_channel_unavailable_error("model_not_found") is True
    assert services._is_channel_unavailable_error("No available channel for model") is True
    assert services._is_channel_unavailable_error("当前分组 default 下对于模型 nano-banana-pro 无可用渠道") is True
    assert services._is_channel_unavailable_error("rate_limit_exceeded") is False

def test_evolink_payload_candidates_for_pro_model():
    task = models.ImageTask(
        task_id="t2",
        prompt="p2",
        model="gemini-3-pro-image-preview",
        aspect_ratio="1:1",
        resolution="1K",
    )
    candidates = services._evolink_payload_candidates(task)
    assert len(candidates) == 2
    assert candidates[0]["model"] == "gemini-3.1-flash-image-preview"
    assert candidates[1]["model"] == "gemini-3-pro-image-preview"


def test_build_evolink_payload_includes_web_search_and_http_images_only():
    local_ref = models.ReferenceImage(
        hash="x",
        file_path="x.png",
        url="/api/uploads/x.png",
        mime_type="image/png",
        original_name="x.png",
    )
    http_ref = models.ReferenceImage(
        hash="y",
        file_path="y.png",
        url="https://example.com/y.png",
        mime_type="image/png",
        original_name="y.png",
    )
    task = models.ImageTask(
        task_id="t",
        prompt="p",
        model="gemini-3.1-flash-image-preview",
        aspect_ratio="1:1",
        resolution="1K",
        params={"web_search": True},
        reference_images=[local_ref, http_ref],
    )

    payload = services._build_evolink_payload(task)
    assert payload["model"] == "gemini-3.1-flash-image-preview"
    assert payload["prompt"] == "p"
    assert payload["tools"] == [{"type": "web_search"}]
    assert payload["image_urls"] == ["https://example.com/y.png"]


def test_pick_evolink_uploaded_url_prefers_file_url():
    body = {
        "success": True,
        "data": {
            "file_url": "https://files.evolink.ai/avatars/a.png",
            "download_url": "https://files.evolink.ai/api/v1/files/download/file_123",
        },
    }
    assert services._pick_evolink_uploaded_url(body) == "https://files.evolink.ai/avatars/a.png"


def test_build_evolink_payload_uses_resolved_image_urls():
    task = models.ImageTask(
        task_id="t3",
        prompt="p3",
        model="gemini-3-pro-image-preview",
        aspect_ratio="1:1",
        resolution="1K",
    )
    payload = services._build_evolink_payload(
        task,
        image_urls=["https://files.evolink.ai/avatars/from-upload.png"],
    )
    assert payload["image_urls"] == ["https://files.evolink.ai/avatars/from-upload.png"]


def test_upload_reference_image_handles_request_errors(tmp_path, monkeypatch):
    file_path = tmp_path / "r.png"
    file_path.write_bytes(b"abc")
    ref = models.ReferenceImage(
        hash="h1",
        file_path=str(file_path),
        url="/api/uploads/r.png",
        mime_type="image/png",
        original_name="r.png",
    )

    class FailClient:
        async def post(self, endpoint, **kwargs):
            raise RuntimeError("network error")

    monkeypatch.setattr(services, "_evolink_upload_base64_path_candidates", lambda: ["/files/upload/base64"])
    monkeypatch.setattr(services, "_evolink_upload_stream_path_candidates", lambda: ["/files/upload/stream"])
    uploaded = asyncio.run(services._upload_reference_image_to_evolink(FailClient(), ref))
    assert uploaded is None


def test_upload_header_candidates_include_x_api_key(monkeypatch):
    monkeypatch.setattr(services, "EVOLINK_API_KEY", "k1")
    headers = services._evolink_upload_header_candidates()
    assert any("x-api-key" in h for h in headers)


def test_apply_model_cost_preference_switches_pro_to_flash():
    class DummyDB:
        async def commit(self):
            return None

    task = models.ImageTask(
        task_id="t4",
        prompt="p4",
        model="gemini-3-pro-image-preview",
        aspect_ratio="1:1",
        resolution="1K",
    )
    asyncio.run(services._apply_model_cost_preference(DummyDB(), task))
    assert task.model == "gemini-3.1-flash-image-preview"
    assert task.params["requested_model"] == "gemini-3-pro-image-preview"
