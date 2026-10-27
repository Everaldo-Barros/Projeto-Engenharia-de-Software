-- Modelo inicial para PostgreSQL (dados exclusivamente fictícios)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE usuarios (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), nome VARCHAR(150) NOT NULL, email VARCHAR(200) NOT NULL UNIQUE, senha_hash TEXT NOT NULL, perfil VARCHAR(20) NOT NULL CHECK (perfil IN ('PACIENTE','PROFISSIONAL','ADMIN')), criado_em TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE pacientes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id), data_nascimento DATE NOT NULL);
CREATE TABLE profissionais (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id), registro_conselho VARCHAR(40) NOT NULL UNIQUE, especialidade VARCHAR(100) NOT NULL);
CREATE TABLE consultas (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), paciente_id UUID NOT NULL REFERENCES pacientes(id), profissional_id UUID NOT NULL REFERENCES profissionais(id), inicio TIMESTAMPTZ NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'AGENDADA' CHECK (status IN ('AGENDADA','CANCELADA','REALIZADA')), criado_em TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE UNIQUE INDEX uq_consulta_profissional_horario_ativo ON consultas (profissional_id, inicio) WHERE status <> 'CANCELADA';
CREATE TABLE registros_clinicos (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), consulta_id UUID NOT NULL UNIQUE REFERENCES consultas(id), texto TEXT NOT NULL, criado_em TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE auditoria (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), usuario_id UUID REFERENCES usuarios(id), acao VARCHAR(120) NOT NULL, data_hora TIMESTAMPTZ NOT NULL DEFAULT now());
-- Regras de autorização e isolamento entre unidades serão aplicadas na API;
-- o esquema não deve ser considerado pronto para dados reais de saúde.
CREATE TABLE IF NOT EXISTS unidades (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), nome VARCHAR(150) NOT NULL, endereco VARCHAR(250) NOT NULL);
CREATE TABLE IF NOT EXISTS profissional_unidades (profissional_id UUID NOT NULL REFERENCES profissionais(id), unidade_id UUID NOT NULL REFERENCES unidades(id), PRIMARY KEY (profissional_id, unidade_id));
ALTER TABLE consultas ADD COLUMN IF NOT EXISTS unidade_id UUID REFERENCES unidades(id);
