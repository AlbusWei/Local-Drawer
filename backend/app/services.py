import asyncio
import hashlib
import os
import time
import base64
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import UploadFile

from google import genai
from google.genai import types

from . import models
from .database import AsyncSessionLocal

def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and os.getenv(key) is None:
            os.environ[key] = value

_load_local_env()

# Global semaphore for concurrency control
MAX_CONCURRENT_TASKS = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

# Gemini Client Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://right.codes/gemini")
gemini_client = genai.Client(api_key=GEMINI_API_KEY, http_options={"base_url": GEMINI_BASE_URL}) if GEMINI_API_KEY else None

# EvoLink (OpenAI-style) Config
EVOLINK_API_KEY = os.getenv("EVOLINK_API_KEY")
EVOLINK_BASE_URL = os.getenv("EVOLINK_BASE_URL", "https://api.evolink.ai/v1").rstrip("/")
EVOLINK_FILE_UPLOAD_PATH = (os.getenv("EVOLINK_FILE_UPLOAD_PATH") or "").strip()
EVOLINK_UPLOAD_PATH = os.getenv("EVOLINK_UPLOAD_PATH", "nanobanana")
EVOLINK_FILE_BASE_URL = (os.getenv("EVOLINK_FILE_BASE_URL") or "").strip().rstrip("/")

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
GENERATED_IMAGES_DIR = BASE_DIR / "generated_images"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

async def calculate_file_hash(file: UploadFile) -> str:
    sha256_hash = hashlib.sha256()
    await file.seek(0)
    while content := await file.read(8192):
        sha256_hash.update(content)
    await file.seek(0)
    return sha256_hash.hexdigest()

async def get_or_create_reference_image(db: AsyncSession, file: UploadFile) -> models.ReferenceImage:
    file_hash = await calculate_file_hash(file)
    
    # Check if exists
    result = await db.execute(select(models.ReferenceImage).where(models.ReferenceImage.hash == file_hash))
    existing_image = result.scalar_one_or_none()
    
    if existing_image:
        return existing_image
        
    # Save new file
    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{file_hash}{ext}"
    file_path = UPLOADS_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        await file.seek(0)
        content = await file.read()
        buffer.write(content)
        
    new_image = models.ReferenceImage(
        hash=file_hash,
        file_path=str(file_path),
        url=f"/api/uploads/{safe_filename}",
        mime_type=file.content_type or "application/octet-stream",
        original_name=file.filename
    )
    db.add(new_image)
    await db.commit()
    await db.refresh(new_image)
    return new_image

def _is_seedream_model(model: str) -> bool:
    model_lower = (model or "").lower()
    return "seedream" in model_lower or model_lower.startswith("doubao-seedream")

def _is_evolink_model(model: str) -> bool:
    return _is_seedream_model(model)

def _gemini_model_priority_candidates(model: str) -> List[str]:
    model_lower = (model or "").lower()
    if model_lower in ("gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview"):
        return ["gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"]
    return [model]

def _is_web_search_supported_on_gemini(model: str) -> bool:
    return (model or "").lower() == "gemini-3.1-flash-image-preview"

def _should_fallback_to_evolink(model: str, error: Exception) -> bool:
    model_lower = (model or "").lower()
    if model_lower not in ("gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"):
        return False
    if not EVOLINK_API_KEY:
        return False
    error_message = str(error).lower()
    fallback_signals = (
        "do_request_failed",
        "upstream error",
        "model_not_found",
        "no available channel",
        "503",
        "500",
    )
    return any(signal in error_message for signal in fallback_signals)

def _is_channel_unavailable_error(error_text: str) -> bool:
    msg = (error_text or "").lower()
    signals = (
        "model_not_found",
        "no available channel",
        "无可用渠道",
    )
    return any(signal in msg for signal in signals)

def _evolink_payload_candidates(task: models.ImageTask, image_urls: Optional[List[str]] = None) -> List[dict]:
    primary = _build_evolink_payload(task, image_urls=image_urls)
    model_candidates = _gemini_model_priority_candidates(task.model)
    payloads: List[dict] = []
    for candidate_model in model_candidates:
        payload = dict(primary)
        payload["model"] = candidate_model
        payloads.append(payload)
    deduped: List[dict] = []
    seen_models = set()
    for payload in payloads:
        model_name = payload.get("model")
        if model_name in seen_models:
            continue
        seen_models.add(model_name)
        deduped.append(payload)
    return deduped

def _is_http_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def _reference_images_to_evolink_urls(task: models.ImageTask) -> List[str]:
    image_urls: List[str] = []
    for ref_img in task.reference_images:
        candidate = (ref_img.url or "").strip()
        if _is_http_url(candidate):
            image_urls.append(candidate)
    return image_urls

def _evolink_upload_base64_path_candidates() -> List[str]:
    if EVOLINK_FILE_UPLOAD_PATH:
        return [EVOLINK_FILE_UPLOAD_PATH]
    candidates = [
        "/files/upload/base64",
        "/files/upload-base64",
        "https://files-api.evolink.ai/api/v1/files/upload/base64",
        "https://files-api.evolink.ai/api/v1/files/upload-base64",
        "https://files.evolink.ai/api/v1/files/upload/base64",
        "https://files.evolink.ai/api/v1/files/upload-base64",
        "https://api.evolink.ai/api/v1/files/upload/base64",
        "https://api.evolink.ai/api/v1/files/upload-base64",
    ]
    if EVOLINK_FILE_BASE_URL:
        candidates = [
            f"{EVOLINK_FILE_BASE_URL}/api/v1/files/upload/base64",
            f"{EVOLINK_FILE_BASE_URL}/api/v1/files/upload-base64",
            *candidates,
        ]
    return candidates

def _evolink_upload_stream_path_candidates() -> List[str]:
    candidates = [
        "/files/upload/stream",
        "/files/upload-stream",
        "/files/upload",
        "https://files-api.evolink.ai/api/v1/files/upload/stream",
        "https://files-api.evolink.ai/api/v1/files/upload-stream",
        "https://files-api.evolink.ai/api/v1/files/upload",
        "https://files.evolink.ai/api/v1/files/upload/stream",
        "https://files.evolink.ai/api/v1/files/upload-stream",
        "https://files.evolink.ai/api/v1/files/upload",
        "https://api.evolink.ai/api/v1/files/upload/stream",
        "https://api.evolink.ai/api/v1/files/upload-stream",
        "https://api.evolink.ai/api/v1/files/upload",
    ]
    if EVOLINK_FILE_BASE_URL:
        candidates = [
            f"{EVOLINK_FILE_BASE_URL}/api/v1/files/upload/stream",
            f"{EVOLINK_FILE_BASE_URL}/api/v1/files/upload-stream",
            f"{EVOLINK_FILE_BASE_URL}/api/v1/files/upload",
            *candidates,
        ]
    return candidates

def _evolink_upload_header_candidates() -> List[dict]:
    if not EVOLINK_API_KEY:
        return [{}]
    return [
        {"Authorization": f"Bearer {EVOLINK_API_KEY}"},
        {"x-api-key": EVOLINK_API_KEY},
        {"Authorization": f"Bearer {EVOLINK_API_KEY}", "x-api-key": EVOLINK_API_KEY},
    ]

def _pick_evolink_uploaded_url(upload_data: dict) -> Optional[str]:
    data = upload_data.get("data")
    if isinstance(data, dict):
        for key in ("file_url", "download_url", "url"):
            candidate = data.get(key)
            if isinstance(candidate, str) and _is_http_url(candidate):
                return candidate
    for key in ("file_url", "download_url", "url"):
        candidate = upload_data.get(key)
        if isinstance(candidate, str) and _is_http_url(candidate):
            return candidate
    return None

def _evolink_upload_payload_candidates(file_name: str, mime_type: str, encoded: str) -> List[dict]:
    data_uri = f"data:{mime_type};base64,{encoded}"
    return [
        {
            "base64_data": encoded,
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
        },
        {
            "base64_data": data_uri,
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
        },
        {
            "base64Data": encoded,
            "fileName": file_name,
            "mimeType": mime_type,
            "uploadPath": EVOLINK_UPLOAD_PATH,
        },
        {
            "Base64Data": encoded,
            "FileName": file_name,
            "MimeType": mime_type,
            "UploadPath": EVOLINK_UPLOAD_PATH,
        },
        {
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
            "base64": encoded,
        },
        {
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
            "file_base64": encoded,
        },
        {
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
            "content_base64": encoded,
        },
        {
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
            "data_uri": data_uri,
        },
        {
            "file_name": file_name,
            "mime_type": mime_type,
            "upload_path": EVOLINK_UPLOAD_PATH,
            "file": data_uri,
        },
    ]

async def _upload_reference_image_to_evolink(http: httpx.AsyncClient, ref_img: models.ReferenceImage) -> Optional[str]:
    file_path = Path(ref_img.file_path)
    if not file_path.exists() or not file_path.is_file():
        return None
    image_bytes = file_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    file_name = (ref_img.original_name or file_path.name or "reference.png").strip() or "reference.png"
    mime_type = (ref_img.mime_type or "application/octet-stream").strip() or "application/octet-stream"
    for endpoint in _evolink_upload_stream_path_candidates():
        for headers in _evolink_upload_header_candidates():
            data = {"upload_path": EVOLINK_UPLOAD_PATH, "file_name": file_name}
            files = {"file": (file_name, image_bytes, mime_type)}
            try:
                resp = await http.post(endpoint, headers=headers, data=data, files=files)
            except Exception:
                continue
            if resp.status_code >= 400:
                continue
            try:
                body = resp.json()
            except Exception:
                continue
            uploaded_url = _pick_evolink_uploaded_url(body)
            if uploaded_url:
                return uploaded_url
    for endpoint in _evolink_upload_base64_path_candidates():
        for headers in _evolink_upload_header_candidates():
            for payload in _evolink_upload_payload_candidates(file_name, mime_type, encoded):
                try:
                    resp = await http.post(endpoint, headers=headers, json=payload)
                except Exception:
                    continue
                if resp.status_code >= 400:
                    continue
                try:
                    body = resp.json()
                except Exception:
                    continue
                uploaded_url = _pick_evolink_uploaded_url(body)
                if uploaded_url:
                    return uploaded_url
    return None

async def _resolve_evolink_reference_images(http: httpx.AsyncClient, task: models.ImageTask) -> List[str]:
    image_urls: List[str] = []
    for ref_img in task.reference_images:
        candidate = (ref_img.url or "").strip()
        if _is_http_url(candidate):
            image_urls.append(candidate)
            continue
        uploaded = await _upload_reference_image_to_evolink(http, ref_img)
        if uploaded:
            image_urls.append(uploaded)
    return image_urls

def _build_evolink_payload(task: models.ImageTask, image_urls: Optional[List[str]] = None) -> dict:
    params = task.params or {}
    payload: dict = {"model": task.model, "prompt": task.prompt}
    for key in ("size", "quality", "n", "prompt_priority", "output_format", "response_format"):
        value = params.get(key)
        if value is not None:
            payload[key] = value
    if image_urls is None and task.reference_images:
        image_urls = _reference_images_to_evolink_urls(task)
    if image_urls:
        payload["image_urls"] = image_urls
    if params.get("web_search"):
        payload["tools"] = [{"type": "web_search"}]
    return payload

async def _run_seedream_task(db: AsyncSession, task: models.ImageTask) -> None:
    if not EVOLINK_API_KEY:
        raise Exception("EVOLINK_API_KEY is not set")

    async with httpx.AsyncClient(
        base_url=EVOLINK_BASE_URL,
        headers={"Authorization": f"Bearer {EVOLINK_API_KEY}"},
        timeout=httpx.Timeout(60.0),
    ) as http:
        resolved_image_urls = await _resolve_evolink_reference_images(http, task)
        if task.reference_images and not resolved_image_urls:
            params = task.params or {}
            params["reference_images_warning"] = "Failed to prepare EvoLink image URLs"
            task.params = params
            await db.commit()
        create_data = None
        create_error = None
        selected_payload = None
        original_model = task.model
        for create_payload in _evolink_payload_candidates(task, image_urls=resolved_image_urls):
            for _ in range(3):
                create_resp = await http.post("/images/generations", json=create_payload)
                if create_resp.status_code < 400:
                    create_data = create_resp.json()
                    selected_payload = create_payload
                    break
                error_text = create_resp.text
                create_error = Exception(f"{create_resp.status_code} {create_resp.reason_phrase}. {error_text}")
                if _is_channel_unavailable_error(error_text):
                    await asyncio.sleep(1)
                    continue
                break
            if create_data:
                break

        if not create_data:
            if create_error:
                raise create_error
            raise Exception("EvoLink create task failed")

        if selected_payload and selected_payload.get("model") and selected_payload["model"] != original_model:
            params = task.params or {}
            params["requested_model"] = original_model
            params["fallback_model"] = selected_payload["model"]
            task.params = params
            task.model = selected_payload["model"]
            await db.commit()

        provider_task_id = create_data.get("id")
        if not provider_task_id:
            raise Exception("EvoLink did not return task id")

        task.provider_task_id = provider_task_id
        await db.commit()

        while True:
            result = await db.execute(select(models.ImageTask).where(models.ImageTask.task_id == task.task_id))
            refreshed = result.scalar_one_or_none()
            if not refreshed:
                return
            if refreshed.status == "CANCELLED":
                return

            status_resp = await http.get(f"/tasks/{provider_task_id}")
            status_resp.raise_for_status()
            status_data = status_resp.json()

            status = status_data.get("status")
            if status in ("pending", "processing"):
                await asyncio.sleep(1)
                continue

            if status == "failed":
                raise Exception(status_data.get("error", {}).get("message") or "EvoLink task failed")

            if status != "completed":
                raise Exception(f"Unexpected EvoLink task status: {status}")

            results = status_data.get("results") or []
            if not results:
                raise Exception("EvoLink task completed but returned no results")

            timestamp = int(time.time())
            output_format = (task.params or {}).get("output_format") or "png"
            output_format = str(output_format).lower().lstrip(".")
            if output_format not in ("png", "jpg", "jpeg", "webp"):
                output_format = "png"
            saved_urls: List[str] = []
            saved_paths: List[str] = []

            for idx, image_url in enumerate(results[:15]):
                image_resp = await http.get(image_url)
                image_resp.raise_for_status()
                image_bytes = image_resp.content

                filename = f"generated_{task.task_id}_{timestamp}_{idx + 1}.{output_format}"
                file_path = GENERATED_IMAGES_DIR / filename
                with open(file_path, "wb") as f:
                    f.write(image_bytes)

                saved_urls.append(f"/api/image/{filename}")
                saved_paths.append(str(file_path))

            task.status = "COMPLETED"
            task.image_url = saved_urls[0]
            task.local_path = saved_paths[0]
            task.image_urls = saved_urls
            task.local_paths = saved_paths
            await db.commit()
            return

async def _run_gemini_task(task: models.ImageTask) -> tuple[str, str]:
    if not gemini_client:
        raise Exception("GEMINI_API_KEY is not set")

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=task.prompt)])]

    for ref_img in task.reference_images:
        with open(ref_img.file_path, "rb") as f:
            image_bytes = f.read()
        contents[0].parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type=ref_img.mime_type)
        )

    params = task.params or {}
    config_kwargs = {
        "response_modalities": ["IMAGE"],
        "image_config": types.ImageConfig(
            aspect_ratio=task.aspect_ratio,
            image_size=task.resolution
        ),
    }
    if params.get("web_search") and _is_web_search_supported_on_gemini(task.model):
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model=task.model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs)
    )

    generated_image_b64 = None
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                generated_image_b64 = part.inline_data.data
                break

    if not generated_image_b64:
        error_parts = ["No image generated from API"]

        if response.candidates and response.candidates[0]:
            candidate = response.candidates[0]
            if candidate.finish_reason:
                error_parts.append(f"Finish Reason: {candidate.finish_reason}")

            if candidate.content and candidate.content.parts:
                text_parts = [p.text for p in candidate.content.parts if p.text]
                if text_parts:
                    error_parts.append(f"Message: {' '.join(text_parts)}")
        else:
            error_parts.append("No candidates returned (possibly blocked by safety filters)")

        raise Exception("; ".join(error_parts))

    timestamp = int(time.time())
    filename = f"generated_{task.task_id}_{timestamp}.png"
    file_path = GENERATED_IMAGES_DIR / filename

    image_data = generated_image_b64
    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)

    with open(file_path, "wb") as f:
        f.write(image_data)

    return f"/api/image/{filename}", str(file_path)

async def _apply_model_cost_preference(db: AsyncSession, task: models.ImageTask) -> None:
    preferred_model = _gemini_model_priority_candidates(task.model)[0]
    if preferred_model == task.model:
        return
    params = task.params or {}
    params["requested_model"] = task.model
    params["preferred_model"] = preferred_model
    task.params = params
    task.model = preferred_model
    await db.commit()

async def process_generation_task(task_id: str):
    """
    Background worker that executes the generation logic.
    Bounded by a semaphore to limit concurrency.
    """
    # Use a new session for the background task
    async with AsyncSessionLocal() as db:
        try:
            # 1. Acquire Semaphore
            async with semaphore:
                # 2. Update status to RUNNING
                result = await db.execute(
                    select(models.ImageTask)
                    .options(selectinload(models.ImageTask.reference_images))
                    .where(models.ImageTask.task_id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if not task:
                    print(f"Task {task_id} not found")
                    return
                
                if task.status == "CANCELLED":
                    print(f"Task {task_id} was cancelled")
                    return

                task.status = "RUNNING"
                await db.commit()
                await _apply_model_cost_preference(db, task)

                if _is_evolink_model(task.model):
                    await _run_seedream_task(db, task)
                else:
                    try:
                        image_url, local_path = await _run_gemini_task(task)
                        task.status = "COMPLETED"
                        task.image_url = image_url
                        task.local_path = local_path
                        await db.commit()
                    except Exception as gemini_error:
                        if _should_fallback_to_evolink(task.model, gemini_error):
                            await _run_seedream_task(db, task)
                        else:
                            raise

        except Exception as e:
            print(f"Task {task_id} failed: {e}")
            # Re-fetch task to avoid detached instance issues if error happened early
            try:
                result = await db.execute(select(models.ImageTask).where(models.ImageTask.task_id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "FAILED"
                    error_message = str(e)
                    # Handle common proxy errors gracefully
                    if "504 Gateway Timeout" in error_message or "Gateway Time-out" in error_message:
                        task.error_msg = "External AI Service Timeout (504). The AI provider (right.codes) is currently overloaded. Please try again later."
                    elif "502 Bad Gateway" in error_message:
                        task.error_msg = "External AI Service Error (502). The AI provider is currently unavailable. Please try again later."
                    else:
                        # Truncate long HTML errors if they occur
                        if len(error_message) > 500 and ("<html" in error_message or "<!DOCTYPE" in error_message):
                            task.error_msg = "External AI Service Error (HTML response). Please check server logs for details."
                        else:
                            task.error_msg = error_message
                            
                    await db.commit()
            except Exception as db_e:
                print(f"Failed to update task status: {db_e}")
