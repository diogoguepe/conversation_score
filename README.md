# Conversation Score — +A Educação

Ferramenta de pontuação automática de atendimentos via WhatsApp/Chat. Recebe transcrições de conversas, processa por múltiplos agentes de IA e retorna scores por critério com justificativas baseadas em evidências.

## Como executar

**Requisitos:** Python 3.9+, conta no Supabase (opcional, para persistência)

```bash
pip install -r requirements.txt
```

Crie um `.env` com base no `.env.example`:

```
GOOGLE_API_KEY=sua_chave_aqui
DATABASE_URL=sua_url_supabase_aqui
```

**API (FastAPI):**
```bash
python api.py
```
Acesse `http://localhost:8000/docs` para o Swagger.

**CLI:**
```bash
python main.py --all                    # avalia todas as sessões
python main.py --session S_27d73d98    # avalia sessão específica
python main.py --list                   # lista sessões disponíveis
```

## Endpoints principais

- `POST /evaluate` — avalia uma conversa e persiste o resultado
- `POST /evaluate/batch` — processa múltiplas sessões em paralelo
- `GET /evaluations` — histórico de avaliações salvas
- `GET /analytics` — média de performance por consultor
- `GET /health` — status da API e conexão com banco

## Privacidade

CPF, e-mail e telefone são substituídos localmente por tags antes de qualquer envio ao Gemini. Nenhum dado sensível chega à API externa.

## Stack

- **LLM:** Google Gemini 2.0 Flash
- **Orquestração:** Agno
- **Backend:** FastAPI
- **Banco:** Supabase (PostgreSQL + SQLModel)
- **Validação:** Pydantic v2
