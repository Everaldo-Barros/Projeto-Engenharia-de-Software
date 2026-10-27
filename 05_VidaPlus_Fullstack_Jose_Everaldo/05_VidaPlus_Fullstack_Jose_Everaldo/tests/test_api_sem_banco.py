"""Testes HTTP do FastAPI sem PostgreSQL, com substitutos de importação."""
import sys
import types
from fastapi.testclient import TestClient

if "psycopg" not in sys.modules:
    psycopg = types.ModuleType("psycopg")
    psycopg.errors = types.SimpleNamespace(UniqueViolation=type("UniqueViolation", (Exception,), {}))
    psycopg.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Banco indisponível"))
    sys.modules["psycopg"] = psycopg
    rows = types.ModuleType("psycopg.rows")
    rows.dict_row = object()
    sys.modules["psycopg.rows"] = rows
if "pwdlib" not in sys.modules:
    pwdlib = types.ModuleType("pwdlib")
    class PasswordHash:
        @classmethod
        def recommended(cls): return cls()
    pwdlib.PasswordHash = PasswordHash
    sys.modules["pwdlib"] = pwdlib

from app.main import app

client = TestClient(app)

def test_saude_http():
    r = client.get("/saude")
    assert r.status_code == 200 and r.json()["status"] == "ok"

def test_rotas_protegidas_sem_token():
    for path in ["/pacientes", "/profissionais", "/consultas"]:
        assert client.get(path).status_code == 401

def test_documentacao_openapi():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/auth/login" in paths and "/consultas" in paths

def test_validacao_admin_email_invalido():
    r = client.post("/admin/inicializar", json={
        "nome": "Teste Acadêmico", "email": "nao-e-email",
        "senha": "senha-ficticia-12345"})
    assert r.status_code == 422

def test_validacao_consulta_uuid_invalido_sem_token():
    r = client.patch("/consultas/id-invalido/cancelar")
    assert r.status_code in (401, 422)
