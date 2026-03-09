from fastapi import FastAPI, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import os

from . import models, schemas, services
from .database import get_db, init_db

# Ensure directories exist
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
app.mount("/api/image", StaticFiles(directory=GENERATED_IMAGES_DIR), name="generated_images")
app.mount("/api/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/api/generate", response_model=schemas.TaskResponse)
async def generate_image(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    model: str = Form("gemini-3.1-flash-image-preview"),
    aspect_ratio: str = Form("1:1"),
    resolution: str = Form("1K"),
    size: Optional[str] = Form(None),
    quality: Optional[str] = Form(None),
    n: Optional[int] = Form(None),
    prompt_priority: Optional[str] = Form(None),
    output_format: Optional[str] = Form(None),
    response_format: Optional[str] = Form(None),
    web_search: Optional[bool] = Form(False),
    images: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db)
):
    # 1. Handle Reference Images (Hash & Deduplicate)
    reference_images = []
    if images:
        for img in images:
            ref_img = await services.get_or_create_reference_image(db, img)
            reference_images.append(ref_img)
    
    # 2. Create Task Record
    task_id = str(uuid.uuid4())
    params = {}
    if size is not None:
        params["size"] = size
    if quality is not None:
        params["quality"] = quality
    if n is not None:
        params["n"] = n
    if prompt_priority is not None:
        params["prompt_priority"] = prompt_priority
    if output_format is not None:
        params["output_format"] = output_format
    if response_format is not None:
        params["response_format"] = response_format
    if web_search:
        params["web_search"] = True
    new_task = models.ImageTask(
        task_id=task_id,
        prompt=prompt,
        model=model,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        params=params or None,
        status="PENDING",
        reference_images=reference_images
    )
    db.add(new_task)
    await db.commit()
    # Reload task with relationships to avoid MissingGreenlet error during serialization
    result = await db.execute(
        select(models.ImageTask)
        .options(selectinload(models.ImageTask.reference_images))
        .where(models.ImageTask.id == new_task.id)
    )
    new_task = result.scalar_one()
    
    # 3. Queue Background Task
    background_tasks.add_task(services.process_generation_task, task_id)
    
    return new_task

@app.get("/api/tasks", response_model=List[schemas.TaskResponse])
async def list_tasks(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.ImageTask)
        .options(selectinload(models.ImageTask.reference_images))
        .order_by(models.ImageTask.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()

@app.get("/api/tasks/{task_id}", response_model=schemas.TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.ImageTask)
        .options(selectinload(models.ImageTask.reference_images))
        .where(models.ImageTask.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ImageTask).where(models.ImageTask.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in ["PENDING", "RUNNING"]:
        task.status = "CANCELLED"
        await db.commit()
        return {"status": "cancelled"}
    else:
        return {"status": "already_completed_or_failed"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ImageTask).where(models.ImageTask.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # We only delete the database record, not the file, as requested by the user.
    # Even if the file is missing, this operation should succeed.
    await db.delete(task)
    await db.commit()
    
    return {"status": "deleted"}
