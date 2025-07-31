import pytest
from fastapi.testclient import TestClient
from io import BytesIO


def test_create_analysis(client: TestClient):
    """Тест создания анализа"""
    # Создаем тестовый аудио файл
    audio_content = b"fake audio content"
    files = {"file": ("test.wav", BytesIO(audio_content), "audio/wav")}
    
    response = client.post("/api/v1/analysis/", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test.wav"
    assert data["status"] == "pending"


def test_get_analyses(client: TestClient):
    """Тест получения списка анализов"""
    response = client.get("/api/v1/analysis/")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)


def test_get_analysis_not_found(client: TestClient):
    """Тест получения несуществующего анализа"""
    response = client.get("/api/v1/analysis/999")
    assert response.status_code == 404


def test_invalid_file_format(client: TestClient):
    """Тест загрузки файла неподдерживаемого формата"""
    files = {"file": ("test.txt", BytesIO(b"text content"), "text/plain")}
    
    response = client.post("/api/v1/analysis/", files=files)
    assert response.status_code == 400 