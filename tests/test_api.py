import pytest
from fastapi.testclient import TestClient
import sys
import os
# Adiciona o diretório src ao sys.path para facilitar importação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_games():
    response = client.get("/api/games?limit=5")
    assert response.status_code == 200
    assert "games" in response.json()
    assert isinstance(response.json()["games"], list)

def test_game_details():
    # Use um appid válido do seu banco, ex: 730
    response = client.get("/api/games/730")
    assert response.status_code in [200, 404]  # 404 se não existir
    if response.status_code == 200:
        assert "game" in response.json()

def test_ml_info():
    response = client.get("/api/ml/info")
    assert response.status_code == 200
    assert "version" in response.json()

def test_ml_predict_single():
    response = client.get("/api/ml/predict/730")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert "recommendation" in response.json()


def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "price_statistics" in data

def test_ml_health_endpoint():
    response = client.get("/api/ml/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data

def test_ml_predict_batch():
    # Testa predição em lote (pode ajustar appids conforme dados reais)
    payload = {"appids": [730, 440, 570]}
    response = client.post("/api/ml/predict/batch", json=payload)
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        assert "predictions" in data

def test_game_not_found():
    response = client.get("/api/games/99999999")
    assert response.status_code == 404

def test_ml_predict_invalid_appid():
    response = client.get("/api/ml/predict/99999999")
    assert response.status_code == 404
