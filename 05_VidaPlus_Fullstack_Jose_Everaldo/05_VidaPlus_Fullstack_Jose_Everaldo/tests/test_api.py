from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get('/saude')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_private_routes_require_token():
    for path in ['/pacientes', '/profissionais', '/consultas']:
        assert client.get(path).status_code == 403


def test_openapi_lists_main_routes():
    paths = client.get('/openapi.json').json()['paths']
    assert '/auth/login' in paths
    assert '/consultas/{consultation_id}/cancelar' in paths
