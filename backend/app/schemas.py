from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TaskCreate(BaseModel):
    prompt: str
    model: str = "gemini-3-pro-image-preview"
    aspect_ratio: str = "1:1"
    resolution: str = "1K"

class ReferenceImageSchema(BaseModel):
    hash: str
    url: str
    original_name: Optional[str]
    mime_type: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    prompt: str
    image_url: Optional[str] = None
    created_at: datetime
    error_msg: Optional[str] = None
    aspect_ratio: str
    resolution: str
    reference_images: List[ReferenceImageSchema] = []

    class Config:
        from_attributes = True
