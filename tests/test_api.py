from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_list_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_task_not_found():
    response = client.get("/api/tasks/not-a-task-id")
    assert response.status_code == 404

# Note: We cannot easily test generate_image without mocking the Gemini API
# or actually calling it (which consumes quota and might fail).
# For now, we test the basic endpoints.
