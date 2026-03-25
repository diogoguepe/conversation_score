import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agents.orchestrator import evaluate_async, evaluate_batch_async
from agents.criteria import CRITERIA
from database import init_db, save_evaluation, list_evaluations, get_consultant_stats

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openapi_tags = [
    {
        "name": "Sistema",
        "description": "Monitoramento e configuração da API.",
    },
    {
        "name": "Avaliação",
        "description": "Endpoints principais para pontuação de conversas via múltiplos agentes de IA.",
    },
    {
        "name": "Analytics",
        "description": "Consultas agregadas para gestão de qualidade e auditoria operacional.",
    },
]

app = FastAPI(
    title="Conversation Score API",
    description=(
        "API de pontuação automática de atendimentos via múltiplos agentes de IA.\n\n"
        "Avalia conversas entre leads e atendentes usando 7 critérios ponderados (C01–C07), "
        "com rastreabilidade completa, detecção de PII e persistência para auditoria humana.\n\n"
        "**Fluxo típico:**\n"
        "1. `POST /evaluate` — envia uma conversa e recebe o score\n"
        "2. `GET /evaluations` — consulta o histórico salvo\n"
        "3. `GET /analytics` — visão gerencial por atendente"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# --- Modelos de Request ---

class ConversationRequest(BaseModel):
    sessionId: str = Field(..., description="Identificador único da sessão de atendimento.")
    messages: List[str] = Field(
        ...,
        description="Lista de mensagens no formato `'human: texto'` ou `'ai: texto'`.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "sessionId": "S_cb815acb",
                "messages": [
                    "human: Oi, quero saber sobre pós-graduação em Marketing.",
                    "ai: Olá! Sou a Beatriz, consultora da +A Code Academy. Você já atua na área?",
                    "human: Sim, trabalho com marketing há 3 anos.",
                    "ai: Ótimo! Nosso MBA em Marketing Digital pode acelerar sua carreira. Qual seu maior desafio hoje?",
                    "human: Preciso aprender sobre dados e performance.",
                    "ai: Perfeito. Temos um módulo completo de Analytics. Posso te enviar a grade curricular?",
                ],
            }
        }
    }


class BatchRequest(BaseModel):
    sessions: List[ConversationRequest] = Field(
        ..., description="Lista de sessões a serem avaliadas em lote."
    )
    max_concurrent: Optional[int] = Field(
        2, ge=1, le=20, description="Número máximo de sessões processadas em paralelo. Padrão: 2. Máximo: 20."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "sessions": [
                    {
                        "sessionId": "S_cb815acb",
                        "messages": [
                            "human: Quero informações sobre pós em RH.",
                            "ai: Olá! Sou a Beatriz da +A Code Academy. Você já atua com RH?",
                            "human: Sim, sou analista há 2 anos.",
                        ],
                    },
                    {
                        "sessionId": "S_de744131",
                        "messages": [
                            "human: Tenho dúvidas sobre o curso de IA.",
                            "ai: Olá! Sou a Beatriz. Você tem experiência com tecnologia?",
                            "human: Sou dev há 5 anos.",
                        ],
                    },
                ],
                "max_concurrent": 2,
            }
        }
    }


# --- Endpoints ---

@app.get(
    "/health",
    summary="Status da API",
    response_description="Status operacional, versão e configuração das integrações.",
    tags=["Sistema"],
)
async def health_check():
    """
    Verifica se a API está operacional.

    Retorna:
    - **status**: `online` se tudo estiver funcionando
    - **version**: versão atual da API
    - **gemini_api**: `configured` se a chave `GOOGLE_API_KEY` estiver presente
    - **database**: `connected` se a `DATABASE_URL` estiver configurada
    """
    return {
        "status": "online",
        "version": "1.0.0",
        "gemini_api": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
        "database": "connected" if os.getenv("DATABASE_URL") else "local-only",
    }


@app.get(
    "/criteria",
    summary="Critérios de avaliação",
    response_description="Lista dos 7 critérios C01–C07 com pesos e descrições.",
    tags=["Sistema"],
)
async def get_criteria():
    """
    Retorna os 7 critérios de avaliação com seus pesos percentuais.

    | Critério | Descrição | Peso |
    |---|---|---|
    | C01 | Saudação e Apresentação | 8% |
    | C02 | Qualificação do Lead | 20% |
    | C03 | Aderência da Recomendação | 20% |
    | C04 | Gestão de Dúvidas e Objeções | 18% |
    | C05 | Clareza e Objetividade | 12% |
    | C06 | Encerramento e Próximos Passos | 12% |
    | C07 | Conformidade Operacional | 10% |
    """
    return CRITERIA


@app.post(
    "/evaluate",
    summary="Avaliar uma conversa",
    response_description="Score completo com nota final, critérios detalhados e contexto extraído.",
    tags=["Avaliação"],
)
async def evaluate_single(request: ConversationRequest):
    """
    Avalia uma única sessão de atendimento e persiste o resultado para auditoria.

    O sistema executa múltiplos agentes em paralelo para analisar cada critério
    e retorna um relatório completo. PII (CPF, e-mail, telefone) é mascarado
    antes de qualquer chamada ao modelo.

    **Retorna:**
    - **nota_final**: float de 0.0 a 10.0
    - **classificacao**: `Insuficiente` | `Regular` | `Bom` | `Excelente`
    - **criterios**: nota e justificativa com evidências para cada C01–C07
    - **contexto**: atendente identificado, lead, curso recomendado, fase da conversa
    - **pontos_de_melhoria**: lista de ações corretivas geradas pelos agentes
    - **db_id**: ID do registro persistido no banco para auditoria
    """
    conversation_text = "\n".join(request.messages)
    try:
        result = await evaluate_async(request.sessionId, conversation_text, request.messages)
        db_id = save_evaluation(result)
        if db_id:
            result["db_id"] = db_id
        return result
    except Exception as e:
        logger.error(f"Erro na avaliação {request.sessionId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/evaluate/batch",
    summary="Avaliar lote de conversas",
    response_description="Lista de scores, um por sessão, na mesma ordem do input.",
    tags=["Avaliação"],
)
async def evaluate_batch_endpoint(request: BatchRequest):
    """
    Processa múltiplas sessões em paralelo com controle de concorrência.

    Usa semáforo interno (`max_concurrent`) para evitar rate limiting da API
    do Gemini. Cada sessão é salva individualmente no banco após a avaliação.

    **Parâmetros:**
    - **sessions**: lista de sessões (cada uma com `sessionId` e `messages`)
    - **max_concurrent**: paralelismo máximo (padrão: 2; recomendado: 2–5)

    **Retorna:** lista de resultados no mesmo formato do `POST /evaluate`,
    preservando a ordem das sessões enviadas.

    > **Dica:** Para lotes grandes (>20 sessões), use `max_concurrent: 2`
    > para evitar erros 429 no plano gratuito do Gemini.
    """
    try:
        results = await evaluate_batch_async(
            [s.model_dump() for s in request.sessions],
            lambda s: "\n".join(s["messages"]),
            max_concurrent=request.max_concurrent,
        )
        for res in results:
            if "sessionId" in res and "nota_final" in res:
                save_evaluation(res)
        return results
    except Exception as e:
        logger.error(f"Erro no processamento em lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/evaluations",
    summary="Histórico de avaliações",
    response_description="Lista paginada de avaliações persistidas, ordenadas da mais recente para a mais antiga.",
    tags=["Analytics"],
)
async def get_history(limit: int = 50):
    """
    Retorna o histórico de avaliações salvas no banco, para auditoria humana.

    **Parâmetros:**
    - **limit** (query): número máximo de registros retornados (padrão: 50)

    **Exemplo:** `GET /evaluations?limit=10`
    """
    return list_evaluations(limit=limit)


@app.get(
    "/analytics",
    summary="Métricas por atendente",
    response_description="Estatísticas agregadas por atendente: média, máximo, mínimo e taxa de identificação.",
    tags=["Analytics"],
)
async def get_analytics():
    """
    Visão gerencial consolidada por atendente.

    Retorna para cada atendente identificado:
    - **atendimentos**: total de sessões avaliadas
    - **media_nota**: média das notas finais
    - **maior_nota** / **menor_nota**: extremos do período
    - **taxa_identificacao**: percentual de sessões onde o atendente se apresentou formalmente

    Sessões onde o atendente não se identificou aparecem como `"Não identificado"`,
    sinalizando falha de conformidade no critério C01.
    """
    return get_consultant_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
