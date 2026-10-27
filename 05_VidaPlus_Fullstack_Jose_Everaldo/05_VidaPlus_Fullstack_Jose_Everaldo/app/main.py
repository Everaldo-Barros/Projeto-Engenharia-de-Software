"""API demonstrativa do VidaPlus. Usar somente dados fictícios."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

import jwt
import psycopg
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

app = FastAPI(title="VidaPlus — API demonstrativa", version="0.1.0")
security = HTTPBearer()
hasher = PasswordHash.recommended()
ROLES = Literal["PACIENTE", "PROFISSIONAL", "ADMIN"]


def config(name: str) -> str:
    value = os.getenv(name)
    if not value or value.startswith("troque_"):
        raise RuntimeError(f"Configure {name} no ambiente")
    return value


@contextmanager
def db():
    with psycopg.connect(config("DATABASE_URL"), row_factory=dict_row) as conn:
        yield conn


class Login(BaseModel):
    email: EmailStr
    senha: str


class UserCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=12, max_length=128)


class PatientCreate(UserCreate):
    data_nascimento: str


class ProfessionalCreate(UserCreate):
    registro_conselho: str = Field(min_length=3, max_length=40)
    especialidade: str = Field(min_length=2, max_length=100)


class UnitCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    endereco: str = Field(min_length=5, max_length=250)


class Booking(BaseModel):
    paciente_id: UUID
    profissional_id: UUID
    unidade_id: UUID
    inicio: datetime


class ClinicalNote(BaseModel):
    texto: str = Field(min_length=3, max_length=10000)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, config("JWT_SECRET"), algorithms=["HS256"])
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(401, "Token inválido") from None
    with db() as conn:
        user = conn.execute("SELECT id, nome, email, perfil FROM usuarios WHERE id = %s", (user_id,)).fetchone()
    if not user:
        raise HTTPException(401, "Usuário inexistente")
    return user


def allow(*roles):
    def check(user=Depends(current_user)):
        if user["perfil"] not in roles:
            raise HTTPException(403, "Acesso não autorizado")
        return user
    return check


def audit(conn, user_id, action):
    conn.execute("INSERT INTO auditoria(usuario_id, acao) VALUES (%s,%s)", (user_id, action))


def create_account(conn, data, role):
    return conn.execute(
        "INSERT INTO usuarios(nome,email,senha_hash,perfil) VALUES (%s,%s,%s,%s) RETURNING id",
        (data.nome, str(data.email), hasher.hash(data.senha), role),
    ).fetchone()["id"]


@app.get("/saude")
def health():
    return {"status": "ok", "ambiente": "demonstracao"}


@app.post("/auth/login")
def login(data: Login):
    with db() as conn:
        user = conn.execute("SELECT id, senha_hash, perfil FROM usuarios WHERE email=%s", (str(data.email),)).fetchone()
    if not user or not hasher.verify(data.senha, user["senha_hash"]):
        raise HTTPException(401, "Credenciais inválidas")
    token = jwt.encode({"sub": str(user["id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, config("JWT_SECRET"), algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "perfil": user["perfil"]}


@app.post("/admin/inicializar", status_code=201)
def bootstrap(data: UserCreate):
    """Permitido somente enquanto não houver nenhum usuário no banco."""
    with db() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(4972245)")
        if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            raise HTTPException(403, "Inicialização já realizada")
        if str(data.email) != config("ADMIN_EMAIL") or data.senha != config("ADMIN_PASSWORD"):
            raise HTTPException(403, "Credenciais de inicialização inválidas")
        uid = create_account(conn, data, "ADMIN")
        audit(conn, uid, "ADMIN_INICIALIZADO")
    return {"id": uid, "perfil": "ADMIN"}


@app.post("/pacientes", status_code=201)
def add_patient(data: PatientCreate, admin=Depends(allow("ADMIN"))):
    try:
        birth = datetime.strptime(data.data_nascimento, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(422, "Data de nascimento inválida (AAAA-MM-DD)") from None
    if birth > datetime.now(timezone.utc).date():
        raise HTTPException(422, "Data de nascimento futura")
    with db() as conn:
        if conn.execute("SELECT 1 FROM usuarios WHERE email=%s", (str(data.email),)).fetchone():
            raise HTTPException(409, "E-mail já cadastrado")
        uid = create_account(conn, data, "PACIENTE")
        patient_id = conn.execute("INSERT INTO pacientes(usuario_id,data_nascimento) VALUES (%s,%s) RETURNING id", (uid, birth)).fetchone()["id"]
        audit(conn, admin["id"], "PACIENTE_CRIADO")
    return {"id": patient_id, "usuario_id": uid}


@app.get("/pacientes")
def list_patients(admin=Depends(allow("ADMIN"))):
    with db() as conn:
        return conn.execute("SELECT p.id, u.nome, u.email, p.data_nascimento FROM pacientes p JOIN usuarios u ON u.id=p.usuario_id ORDER BY u.nome").fetchall()


@app.post("/profissionais", status_code=201)
def add_professional(data: ProfessionalCreate, admin=Depends(allow("ADMIN"))):
    with db() as conn:
        if conn.execute("SELECT 1 FROM usuarios WHERE email=%s", (str(data.email),)).fetchone():
            raise HTTPException(409, "E-mail já cadastrado")
        if conn.execute("SELECT 1 FROM profissionais WHERE registro_conselho=%s", (data.registro_conselho,)).fetchone():
            raise HTTPException(409, "Registro profissional já cadastrado")
        uid = create_account(conn, data, "PROFISSIONAL")
        pid = conn.execute("INSERT INTO profissionais(usuario_id,registro_conselho,especialidade) VALUES (%s,%s,%s) RETURNING id", (uid, data.registro_conselho, data.especialidade)).fetchone()["id"]
        audit(conn, admin["id"], "PROFISSIONAL_CRIADO")
    return {"id": pid, "usuario_id": uid}


@app.get("/profissionais")
def list_professionals(user=Depends(current_user)):
    with db() as conn:
        return conn.execute("SELECT p.id,u.nome,p.especialidade FROM profissionais p JOIN usuarios u ON u.id=p.usuario_id ORDER BY u.nome").fetchall()


@app.post("/unidades", status_code=201)
def add_unit(data: UnitCreate, admin=Depends(allow("ADMIN"))):
    with db() as conn:
        uid = conn.execute("INSERT INTO unidades(nome,endereco) VALUES (%s,%s) RETURNING id", (data.nome, data.endereco)).fetchone()["id"]
        audit(conn, admin["id"], "UNIDADE_CRIADA")
    return {"id": uid}


@app.post("/unidades/{unit_id}/profissionais/{professional_id}")
def link_professional(unit_id: UUID, professional_id: UUID, admin=Depends(allow("ADMIN"))):
    with db() as conn:
        if not conn.execute("SELECT 1 FROM unidades WHERE id=%s", (unit_id,)).fetchone() or not conn.execute("SELECT 1 FROM profissionais WHERE id=%s", (professional_id,)).fetchone():
            raise HTTPException(404, "Unidade ou profissional inexistente")
        conn.execute("INSERT INTO profissional_unidades(profissional_id,unidade_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (professional_id, unit_id))
        audit(conn, admin["id"], "PROFISSIONAL_VINCULADO")
    return {"status": "vinculado"}


@app.post("/consultas", status_code=201)
def book(data: Booking, user=Depends(allow("ADMIN", "PACIENTE"))):
    if data.inicio.tzinfo is None or data.inicio <= datetime.now(timezone.utc):
        raise HTTPException(422, "Informe horário futuro com fuso horário")
    with db() as conn:
        if user["perfil"] == "PACIENTE":
            own = conn.execute("SELECT id FROM pacientes WHERE usuario_id=%s", (user["id"],)).fetchone()
            if not own or own["id"] != data.paciente_id:
                raise HTTPException(403, "Não é possível agendar para outro paciente")
        if not conn.execute("SELECT 1 FROM pacientes WHERE id=%s", (data.paciente_id,)).fetchone():
            raise HTTPException(404, "Paciente não encontrado")
        if not conn.execute("SELECT 1 FROM profissional_unidades WHERE profissional_id=%s AND unidade_id=%s", (data.profissional_id, data.unidade_id)).fetchone():
            raise HTTPException(422, "Profissional não vinculado à unidade")
        try:
            cid = conn.execute("INSERT INTO consultas(paciente_id,profissional_id,unidade_id,inicio) VALUES (%s,%s,%s,%s) RETURNING id", (data.paciente_id, data.profissional_id, data.unidade_id, data.inicio)).fetchone()["id"]
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409, "Horário já ocupado") from None
        audit(conn, user["id"], "CONSULTA_AGENDADA")
    return {"id": cid, "status": "AGENDADA"}


@app.get("/consultas")
def list_bookings(user=Depends(current_user)):
    query = "SELECT c.id,c.paciente_id,c.profissional_id,c.unidade_id,c.inicio,c.status FROM consultas c"
    params = ()
    if user["perfil"] == "PACIENTE":
        query += " JOIN pacientes p ON p.id=c.paciente_id WHERE p.usuario_id=%s"
        params = (user["id"],)
    elif user["perfil"] == "PROFISSIONAL":
        query += " JOIN profissionais p ON p.id=c.profissional_id WHERE p.usuario_id=%s"
        params = (user["id"],)
    with db() as conn:
        return conn.execute(query + " ORDER BY c.inicio", params).fetchall()


@app.patch("/consultas/{consultation_id}/cancelar")
def cancel(consultation_id: UUID, user=Depends(allow("ADMIN", "PACIENTE"))):
    with db() as conn:
        row = conn.execute("SELECT c.status,p.usuario_id FROM consultas c JOIN pacientes p ON p.id=c.paciente_id WHERE c.id=%s FOR UPDATE OF c", (consultation_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Consulta não encontrada")
        if user["perfil"] == "PACIENTE" and row["usuario_id"] != user["id"]:
            raise HTTPException(403, "Acesso não autorizado")
        if row["status"] != "AGENDADA":
            raise HTTPException(409, "Consulta não pode ser cancelada")
        conn.execute("UPDATE consultas SET status='CANCELADA' WHERE id=%s", (consultation_id,))
        audit(conn, user["id"], "CONSULTA_CANCELADA")
    return {"status": "CANCELADA"}


@app.post("/consultas/{consultation_id}/registro", status_code=201)
def clinical_record(consultation_id: UUID, data: ClinicalNote, user=Depends(allow("PROFISSIONAL"))):
    with db() as conn:
        row = conn.execute("SELECT c.id,c.status FROM consultas c JOIN profissionais p ON p.id=c.profissional_id WHERE c.id=%s AND p.usuario_id=%s FOR UPDATE OF c", (consultation_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Consulta não encontrada para este profissional")
        if row["status"] != "AGENDADA":
            raise HTTPException(409, "Consulta não está agendada")
        if conn.execute("SELECT 1 FROM registros_clinicos WHERE consulta_id=%s", (consultation_id,)).fetchone():
            raise HTTPException(409, "Atendimento já registrado")
        conn.execute("INSERT INTO registros_clinicos(consulta_id,texto) VALUES (%s,%s)", (consultation_id, data.texto))
        conn.execute("UPDATE consultas SET status='REALIZADA' WHERE id=%s", (consultation_id,))
        audit(conn, user["id"], "ATENDIMENTO_REGISTRADO")
    return {"status": "REALIZADA"}


# Front-end servido pela própria API: mesma origem, sem configuração de CORS.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True), name="frontend")
