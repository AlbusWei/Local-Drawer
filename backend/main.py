from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
import uvicorn
import os
import json
import time
import base64
from typing import List, Optional

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path

# Constants
BASE_DIR = Path(__file__).resolve().parent
GENERATED_IMAGES_DIR = BASE_DIR / "generated_images"
UPLOADS_DIR = BASE_DIR / "uploads"
HISTORY_FILE = BASE_DIR / "history.json"
API_KEY = "sk-9a3fa4e2455f413f8a176ac7e85444fd"
BASE_URL = "https://right.codes/gemini/v1beta/" # Removed 'models/' as SDK usually appends it

# Ensure directories exist
GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

if not HISTORY_FILE.exists():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# Mount static files
app.mount("/api/image", StaticFiles(directory=str(GENERATED_IMAGES_DIR)), name="generated_images")
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Pydantic models
class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gemini-3-pro-image" # Default model

class ImageRecord(BaseModel):
    id: str
    image_url: str
    prompt: str
    created_at: str

class GenerateResponse(BaseModel):
    success: bool
    image_url: str
    prompt: str
    created_at: str

# Gemini Client
client = genai.Client(
    api_key=API_KEY,
    http_options={'base_url': BASE_URL}
)

@app.get("/")
async def root():
    return {"message": "Nano Banana Pro API is running"}

@app.get("/api/history", response_model=List[ImageRecord])
async def get_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_image(
    prompt: str = Form(...),
    model: str = Form("gemini-3-pro-image"),
    image: UploadFile = File(None)
):
    try:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

        if image:
            # Save uploaded image
            upload_path = os.path.join(UPLOADS_DIR, image.filename)
            with open(upload_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            # Read image for API
            with open(upload_path, "rb") as f:
                image_bytes = f.read()
                
            # Add image to contents for image-to-image generation
            # Note: SDK expects base64 or file upload, here we use inline_data if supported or bytes
            # checking SDK docs, usually we can pass bytes or upload file first
            # Since this is custom endpoint, let's try inline data
            
            contents[0].parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=image.content_type or "image/jpeg")
            )

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        generated_image_b64 = None
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    generated_image_b64 = part.inline_data.data
                    break
        
        if not generated_image_b64:
             raise HTTPException(status_code=500, detail="No image generated")

        # Save generated image
        timestamp = int(time.time())
        filename = f"generated_{timestamp}.png"
        file_path = os.path.join(GENERATED_IMAGES_DIR, filename)
        
        image_data = base64.b64decode(generated_image_b64)
        with open(file_path, "wb") as f:
            f.write(image_data)
            
        image_url = f"/api/image/{filename}"
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        
        record = {
            "id": str(timestamp),
            "image_url": image_url,
            "prompt": prompt,
            "created_at": created_at,
            "file_path": file_path
        }
        
        # Update history
        with open(HISTORY_FILE, "r+") as f:
            history = json.load(f)
            history.insert(0, record)
            f.seek(0)
            json.dump(history, f)
            f.truncate()
            
        return {
            "success": True,
            "image_url": image_url,
            "prompt": prompt,
            "created_at": created_at
        }

    except Exception as e:
        print(f"Error generating image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
