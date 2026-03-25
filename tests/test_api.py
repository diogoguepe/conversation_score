"""
Testes da API FastAPI — endpoints, validação de payloads e health check.
Usa httpx + AsyncClient para testar sem precisar de LLM.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from api import app


@pytest.mark.anyio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["version"] == "1.0.0"


@pytest.mark.anyio
async def test_list_criteria():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/criteria")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert "C01" in data
    assert "C07" in data
    # Verifica estrutura de cada criterio
    c01 = data["C01"]
    assert "name" in c01
    assert "weight" in c01
    assert "rubric" in c01


@pytest.mark.anyio
async def test_evaluate_validation_error():
    """Deve rejeitar payload sem campos obrigatórios."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/evaluate", json={})
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.anyio
async def test_evaluate_batch_validation():
    """Deve rejeitar batch com max_concurrent fora do range."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/evaluate/batch", json={
            "sessions": [],
            "max_concurrent": 100,  # max permitido é 20
        })
    assert response.status_code == 422


@pytest.mark.anyio
async def test_docs_endpoint():
    """Swagger docs deve estar acessível."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 200
