# VidaPlus — Etapa 5: interface web integrada

**Acadêmico:** José Everaldo de Barros — RU 4972245.

Este pacote contém o Back-end da etapa 4 e uma interface web responsiva (HTML, CSS e JavaScript), servida pela própria aplicação FastAPI. É um protótipo acadêmico, somente com dados fictícios.

## Execução

1. Instale Python 3.11+ e Docker Desktop (ou Docker Engine com Compose).
2. Copie `.env.example` para `.env` e substitua chaves/senhas; mantenha a senha do banco sincronizada com a URL de conexão.
3. Inicie o PostgreSQL: `docker compose up -d db`.
4. Crie e ative o ambiente virtual: `python -m venv .venv`; Linux/macOS: `source .venv/bin/activate`; Windows PowerShell: `.venv\Scripts\Activate.ps1`.
5. Instale: `pip install -r requirements.txt`.
6. Carregue as variáveis de `.env` no ambiente (veja o `README.md` da API).
7. Inicie: `uvicorn app.main:app --reload`.
8. Acesse **http://127.0.0.1:8000/**. A documentação da API está em `/docs`.
9. Na primeira execução, inicialize o administrador com as credenciais definidas em `.env` e faça login.

## Fluxo de demonstração

1. Entrar como administrador.
2. Cadastrar um paciente e guardar o ID exibido.
3. Cadastrar um profissional.
4. Cadastrar uma unidade e guardar seu ID.
5. Vincular profissional e unidade.
6. Agendar consulta para uma data futura; consultar listagem e cancelar, se desejado.
7. Entrar como profissional e registrar um atendimento de exemplo.

## Limitações e cuidados

- A API ainda não tem `GET /unidades`, então o ID da unidade deve ser copiado após o cadastro.
- O cadastro de pacientes não é listado para perfis não administrativos; pacientes devem informar o próprio ID para agendar.
- Tokens ficam **somente na memória** do navegador e são perdidos ao recarregar a página.
- A interface não deve ser usada com dados pessoais ou clínicos reais. Não há evidência de testes integrados completos nem de implantação em produção.
- O fluxo de registro clínico é demonstrativo, não um prontuário eletrônico homologado.
