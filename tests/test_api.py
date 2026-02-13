from fastapi.testclient import TestClient
from backend.main import app
import os

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Nano Banana Pro API is running"}

def test_get_history():
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# Note: We cannot easily test generate_image without mocking the Gemini API
# or actually calling it (which consumes quota and might fail).
# For now, we test the basic endpoints.
