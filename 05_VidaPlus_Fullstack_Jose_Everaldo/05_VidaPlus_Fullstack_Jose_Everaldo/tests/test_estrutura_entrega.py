"""Verificações estáticas do protótipo VidaPlus, sem banco de dados."""
from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

def test_arquivos_principais():
    for item in ["app/main.py", "frontend/index.html", "frontend/app.js",
                 "frontend/style.css", "schema.sql", "requirements.txt",
                 "docker-compose.yml", ".env.example"]:
        assert (ROOT / item).is_file(), item

def test_codigo_python_compila():
    compile(SOURCE, str(ROOT / "app/main.py"), "exec")

def test_rotas_principais_declaradas():
    expected = ["/saude", "/auth/login", "/admin/inicializar", "/pacientes",
                "/profissionais", "/unidades", "/consultas",
                "/consultas/{consultation_id}/cancelar",
                "/consultas/{consultation_id}/registro"]
    for path in expected:
        assert any(path == a.value for node in ast.walk(TREE) if isinstance(node, ast.Call) for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)), path

def test_protecao_rotas_e_hash_de_senha():
    assert "PasswordHash.recommended()" in SOURCE
    assert "jwt.decode(" in SOURCE and "jwt.encode(" in SOURCE
    assert 'Depends(allow("ADMIN"))' in SOURCE

def test_schema_e_relacionamentos():
    sql = (ROOT / "schema.sql").read_text(encoding="utf-8").lower()
    for table in ["usuarios", "pacientes", "profissionais", "unidades",
                  "consultas", "auditoria"]:
        assert ("create table " + table) in sql or ("create table if not exists " + table) in sql, table
    assert "references" in sql

def test_interface_web():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert "VidaPlus" in html
    assert "inicializar" in js
    assert "login" in js

def test_arquivo_de_segredos_nao_incluido():
    assert not (ROOT / ".env").exists()
