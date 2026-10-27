# VidaPlus — Etapa 4: Back-end (MVP acadêmico)

Projeto: Sistema de Gestão Hospitalar e de Serviços de Saúde (SGHSS) — VidaPlus.  
Acadêmico: José Everaldo de Barros | RU 4972245.

## Requisitos

- Python 3.11 ou superior
- Docker com Docker Compose (para PostgreSQL)

## Como executar

1. Copie `.env.example` para `.env` e **substitua todas as senhas e chaves**. Use senhas longas, e mantenha `DATABASE_URL` consistente com `POSTGRES_PASSWORD`.
2. Inicie o banco: `docker compose up -d db`.
3. Crie o ambiente virtual: `python -m venv .venv` e ative-o (`source .venv/bin/activate` no Linux/macOS; `.venv\\Scripts\\activate` no Windows).
4. Instale dependências: `pip install -r requirements.txt`.
5. Carregue variáveis do arquivo `.env` no terminal. Linux/macOS: `set -a; source .env; set +a`. PowerShell: `$env:DATABASE_URL='...'; $env:JWT_SECRET='...'; $env:ADMIN_EMAIL='...'; $env:ADMIN_PASSWORD='...'` (ou use um gerenciador de variáveis de ambiente).
6. Inicie a API: `uvicorn app.main:app --reload`.
7. Acesse `http://127.0.0.1:8000/docs`.

### Inicialização

Com o banco vazio, execute `POST /admin/inicializar` com nome, e-mail idêntico a `ADMIN_EMAIL` e senha idêntica a `ADMIN_PASSWORD` (mínimo 12 caracteres). Esse endpoint funciona **somente quando a tabela de usuários está vazia**. Em seguida, use `POST /auth/login`, copie o `access_token` e clique em **Authorize** no Swagger (ícone de cadeado) para acessar as rotas protegidas.

Ordem recomendada: criar paciente; criar profissional; criar unidade; vincular profissional à unidade; agendar consulta; listar ou cancelar consulta. Para registrar atendimento, entre com a conta do profissional cadastrado.

## Rotas

| Método | Caminho | Acesso |
|---|---|---|
| GET | `/saude` | público |
| POST | `/admin/inicializar` | configuração inicial, banco vazio |
| POST | `/auth/login` | público |
| POST/GET | `/pacientes` | administrador |
| POST/GET | `/profissionais` | administrador / autenticado (GET) |
| POST | `/unidades` | administrador |
| POST | `/unidades/{unidade}/profissionais/{profissional}` | administrador |
| POST/GET | `/consultas` | administrador ou paciente (POST); autenticado (GET) |
| PATCH | `/consultas/{id}/cancelar` | administrador ou paciente titular |
| POST | `/consultas/{id}/registro` | profissional responsável |

## Testes

`pytest -q`

Os testes automatizados incluídos são básicos e não substituem testes integrados com PostgreSQL. O ambiente não contém demonstração de implantação em produção. Testes de carga, recuperação, segurança avançada e conformidade legal ficam pendentes.

## Limitações conhecidas

- Protótipo acadêmico **não apropriado para dados reais de saúde**.
- A autenticação usa JWT de uma hora e senha com hash Argon2; faltam limitação de tentativas, rotação/revogação de tokens e fluxos de recuperação de senha.
- Horários disponíveis e duração de consultas ainda não são modelados; o conflito impede apenas coincidência exata do horário inicial.
- Atualização de cadastros, acesso ao histórico clínico, notificações e interfaces web ainda não foram implementados.
- O script `schema.sql` é aplicado pelo Docker somente na **primeira criação** do volume de dados. Não execute `docker compose down -v` se houver dados a preservar.
- Em implantação real seriam necessários HTTPS, segregação de dados, políticas de retenção, backup, avaliação LGPD e revisão especializada.
