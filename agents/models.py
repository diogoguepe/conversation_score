from typing import List, Optional
from pydantic import BaseModel, Field

class ContextResult(BaseModel):
    consultor: Optional[str] = Field(None, description="Nome do consultor")
    lead: Optional[str] = Field(None, description="Identificador do lead")
    curso_interesse: Optional[str] = Field(None, description="Cursos citados")
    perfil_lead: Optional[str] = Field(None, description="Resumo do perfil profissional")
    objetivo_lead: Optional[str] = Field(None, description="Objetivo principal")
    fase_atingida: str = Field(..., description="qualificacao | recomendacao | duvidas | encerramento")
    observacoes: Optional[str] = Field(None, description="Pontos relevantes extras")

class CriterionResult(BaseModel):
    nota: float = Field(..., ge=0, le=10)
    justificativa: str = Field(..., description="2-3 frases com evidências da conversa")

class SalesResults(BaseModel):
    C02: CriterionResult
    C03: CriterionResult

class CommunicationResults(BaseModel):
    C01: CriterionResult
    C04: CriterionResult
    C05: CriterionResult

class ProcessResults(BaseModel):
    C06: CriterionResult
    C07: CriterionResult
