from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel

from agents.criteria import CRITERIA
from agents.models import (
    ContextResult,
    SalesResults,
    CommunicationResults,
    ProcessResults
)


def _gemini() -> Gemini:
    return Gemini(id="gemini-2.0-flash")


def build_context_agent() -> Agent:
    """Extrai metadados da conversa (lead, consultor, fase). Não pontua critérios."""
    return Agent(
        name="Analisador de Contexto",
        role="Extrai metadados contextuais da conversa para fins de auditoria e rastreabilidade",
        model=_gemini(),
        response_model=ContextResult,
        instructions=[
            "Você analisa transcrições de conversas entre consultores e leads de pós-graduação.",
            "Identifique quando o consultor se apresenta na conversa (ex: 'eu sou [NOME], consultora/consultor da +A').",
            "Extraia o nome do consultor preferencialmente da primeira mensagem da IA ou de qualquer mensagem onde ele se identifique.",
            "Se nenhum nome for encontrado, retorne null no campo consultor.",
            "Extraia as demais informações estruturadas da conversa.",
            "Baseie-se APENAS no texto fornecido.",
        ],
    )


def build_sales_agent() -> Agent:
    """Avalia C02 — Qualificação do Lead e C03 — Aderência da Recomendação."""
    c02 = CRITERIA["C02"]
    c03 = CRITERIA["C03"]
    return Agent(
        name="Avaliador de Vendas",
        role="Avalia a qualidade da qualificação do lead e a aderência da recomendação de curso",
        model=_gemini(),
        response_model=SalesResults,
        instructions=[
            "Você avalia conversas de consultoria educacional. Foco exclusivo em duas dimensões de vendas.",
            "",
            f"CRITÉRIO C02 — {c02['name']} (peso {int(c02['weight']*100)}%)",
            f"Descrição: {c02['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c02["rubric"].items()],
            "",
            f"CRITÉRIO C03 — {c03['name']} (peso {int(c03['weight']*100)}%)",
            f"Descrição: {c03['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c03["rubric"].items()],
            "",
            "Se a conversa for muito curta para avaliar C03 (nenhuma recomendação foi feita), atribua nota proporcional ao que foi possível observar.",
            "Baseie TODAS as justificativas em trechos concretos da conversa.",
        ],
    )


def build_communication_agent() -> Agent:
    """Avalia C01 — Saudação, C04 — Gestão de Objeções e C05 — Clareza."""
    c01 = CRITERIA["C01"]
    c04 = CRITERIA["C04"]
    c05 = CRITERIA["C05"]
    return Agent(
        name="Avaliador de Comunicação",
        role="Avalia saudação, gestão de objeções e clareza na comunicação",
        model=_gemini(),
        response_model=CommunicationResults,
        instructions=[
            "Você avalia conversas de consultoria educacional. Foco exclusivo em três dimensões de comunicação.",
            "",
            f"CRITÉRIO C01 — {c01['name']} (peso {int(c01['weight']*100)}%)",
            f"Descrição: {c01['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c01["rubric"].items()],
            "",
            f"CRITÉRIO C04 — {c04['name']} (peso {int(c04['weight']*100)}%)",
            f"Descrição: {c04['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c04["rubric"].items()],
            "",
            f"CRITÉRIO C05 — {c05['name']} (peso {int(c05['weight']*100)}%)",
            f"Descrição: {c05['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c05["rubric"].items()],
            "",
            "Se não houve objeções na conversa, avalie C04 com base na proatividade do consultor em antecipar dúvidas.",
            "Baseie TODAS as justificativas em trechos concretos da conversa.",
        ],
    )


def build_process_agent() -> Agent:
    """Avalia C06 — Encerramento e C07 — Conformidade Operacional."""
    c06 = CRITERIA["C06"]
    c07 = CRITERIA["C07"]
    return Agent(
        name="Avaliador de Processo",
        role="Avalia encerramento da conversa e conformidade com procedimentos operacionais",
        model=_gemini(),
        response_model=ProcessResults,
        instructions=[
            "Você avalia conversas de consultoria educacional. Foco exclusivo em processo e conformidade.",
            "",
            f"CRITÉRIO C06 — {c06['name']} (peso {int(c06['weight']*100)}%)",
            f"Descrição: {c06['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c06["rubric"].items()],
            "",
            f"CRITÉRIO C07 — {c07['name']} (peso {int(c07['weight']*100)}%)",
            f"Descrição: {c07['description']}",
            "Rubrica:",
            *[f"  {k}: {v}" for k, v in c07["rubric"].items()],
            "",
            "Para C07, verifique especialmente:",
            "  - Preços foram informados diretamente? (violação — deve encaminhar ao especialista)",
            "  - Dados pessoais foram tratados adequadamente?",
            "  - O fluxo de transferência para especialista foi seguido quando necessário?",
            "",
            "Baseie TODAS as justificativas em trechos concretos da conversa.",
        ],
    )


def build_synthesis_agent() -> Agent:
    """Consolida os resultados parciais de blocos numa avaliação final única."""
    class FinalSynthesis(BaseModel):
        sales: SalesResults
        communication: CommunicationResults
        process: ProcessResults

    return Agent(
        model=Gemini(id="gemini-2.0-flash"),
        description="Você é o Coordenador Senior de Qualidade da +A Code Academy.",
        instructions=[
            "Você receberá dados de avaliações de diferentes partes ou perspectivas de uma conversa.",
            "Sua tarefa é sintetizar esses resultados em uma única avaliação final equilibrada.",
            "Para critérios de início (Saudação), priorize o que aconteceu no começo.",
            "Para critérios de fim (Encerramento/CTA), foque no que aconteceu no encerramento.",
            "Para critérios contínuos (Comunicação/Engajamento), faça uma visão holística de todo o atendimento.",
            "Retorne o resultado estritamente seguindo o modelo de resposta.",
            "Justifique cada nota com base no resumo consolidado das evidências apresentadas.",
        ],
        response_model=FinalSynthesis,
    )
