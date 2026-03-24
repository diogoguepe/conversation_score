import pytest
from agents.models import CriterionResult, ContextResult, SalesResults

def test_criterion_result_validation():
    # Nota válida
    cr = CriterionResult(nota=8.5, justificativa="Excelente!")
    assert cr.nota == 8.5
    
    # Nota fora do limite (ge=0, le=10)
    with pytest.raises(ValueError):
        CriterionResult(nota=15.0, justificativa="Erro")

def test_context_result():
    ctx = ContextResult(
        consultor="Beatriz",
        lead="Lead_001",
        fase_atingida="qualificacao"
    )
    assert ctx.consultor == "Beatriz"
    assert ctx.fase_atingida == "qualificacao"

def test_sales_results():
    sr = SalesResults(
        C02=CriterionResult(nota=9, justificativa="Bom"),
        C03=CriterionResult(nota=7, justificativa="Regular")
    )
    assert sr.C02.nota == 9
    assert sr.C03.nota == 7
