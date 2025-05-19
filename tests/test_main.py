import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200

def test_generate_docker_invalid_file():
    # Test with non-zip file
    files = {
        'file': ('test.txt', b'not a zip file', 'text/plain')
    }
    response = client.post("/generate-docker", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be a ZIP archive"

def test_generate_k8s_invalid_file():
    # Test with non-zip file
    files = {
        'file': ('test.txt', b'not a zip file', 'text/plain')
    }
    response = client.post("/generate-k8s", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be a ZIP archive" 