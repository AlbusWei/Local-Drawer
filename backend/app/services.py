import asyncio
import hashlib
import os
import time
import base64
from pathlib import Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import UploadFile

from google import genai
from google.genai import types

from . import models
from .database import AsyncSessionLocal

# Global semaphore for concurrency control
MAX_CONCURRENT_TASKS = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

# Gemini Client Config
API_KEY = "sk-9a3fa4e2455f413f8a176ac7e85444fd"
BASE_URL = "https://right.codes/gemini"
client = genai.Client(api_key=API_KEY, http_options={'base_url': BASE_URL})

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
                
                # 3. Prepare Gemini Request
                contents = [types.Content(role="user", parts=[types.Part.from_text(text=task.prompt)])]
                
                # Load reference images
                for ref_img in task.reference_images:
                    with open(ref_img.file_path, "rb") as f:
                        image_bytes = f.read()
                    contents[0].parts.append(
                        types.Part.from_bytes(data=image_bytes, mime_type=ref_img.mime_type)
                    )
                
                # 4. Call API
                # Note: The SDK call is synchronous, so we run it in a thread pool to avoid blocking the event loop
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=task.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=task.aspect_ratio,
                            image_size=task.resolution
                        )
                    )
                )

                # 5. Process Result
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
                        
                        # Check if there is text content explaining the refusal
                        if candidate.content and candidate.content.parts:
                            text_parts = [p.text for p in candidate.content.parts if p.text]
                            if text_parts:
                                error_parts.append(f"Message: {' '.join(text_parts)}")
                    else:
                        error_parts.append("No candidates returned (possibly blocked by safety filters)")
                                 
                    raise Exception("; ".join(error_parts))

                # Save Image
                timestamp = int(time.time())
                filename = f"generated_{task_id}_{timestamp}.png"
                file_path = GENERATED_IMAGES_DIR / filename
                
                image_data = generated_image_b64
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                    
                with open(file_path, "wb") as f:
                    f.write(image_data)
                
                # 6. Update Task Success
                task.status = "COMPLETED"
                task.image_url = f"/api/image/{filename}"
                task.local_path = str(file_path)
                await db.commit()

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
