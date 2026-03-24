import pytest
from agents.orchestrator import _classify, _consolidate, MAX_RETRIES, RETRY_BASE_DELAY
from agents.criteria import CRITERIA


def test_classify_logic():
    assert _classify(9.5) == "Excelente"
    assert _classify(9.0) == "Excelente"
    assert _classify(7.5) == "Bom"
    assert _classify(7.0) == "Bom"
    assert _classify(5.5) == "Regular"
    assert _classify(5.0) == "Regular"
    assert _classify(3.0) == "Insuficiente"
    assert _classify(0.0) == "Insuficiente"


def test_consolidate_all_tens():
    """Se todos os critérios recebem nota 10, a nota final deve ser 10.0."""
    raw_criteria = {
        cid: {"nota": 10.0, "justificativa": "Perfeito."} for cid in CRITERIA.keys()
    }
    result = _consolidate("S_TEST", {}, raw_criteria, 5.0, {})
    
    assert result["nota_final"] == 10.0
    assert result["classificacao"] == "Excelente"
    assert result["tempo_s"] == 5.0
    assert result["sessionId"] == "S_TEST"


def test_consolidate_all_zeros():
    """Se todos os critérios recebem nota 0, a nota final deve ser 0.0."""
    raw_criteria = {
        cid: {"nota": 0.0, "justificativa": "Péssimo."} for cid in CRITERIA.keys()
    }
    result = _consolidate("S_ZERO", {}, raw_criteria, 1.0, {})
    
    assert result["nota_final"] == 0.0
    assert result["classificacao"] == "Insuficiente"


def test_consolidate_partial():
    """Se apenas C01 (8%) recebe nota 10 e o resto é omitido, nota = 0.8."""
    raw_criteria = {
        "C01": {"nota": 10.0, "justificativa": "Excelente saudação."}
    }
    result = _consolidate("S_PARTIAL", {}, raw_criteria, 1.0, {})
    
    assert result["nota_final"] == 0.8
    assert result["avaliacao"]["C02"]["nota"] == 0.0
    assert result["avaliacao"]["C02"]["justificativa"] == "Não avaliado."


def test_consolidate_with_errors():
    """Verifica que erros de agentes são incluídos no resultado."""
    raw_criteria = {}
    agent_errors = {"sales": Exception("API timeout")}
    
    result = _consolidate("S_ERR", {}, raw_criteria, 2.0, agent_errors)
    
    assert "avisos" in result
    assert "sales" in result["avisos"]
    assert "API timeout" in result["avisos"]["sales"]


def test_consolidate_with_pydantic_context():
    """Testa que o contexto Pydantic é convertido para dict."""
    from agents.models import ContextResult
    
    ctx = ContextResult(
        consultor="Beatriz",
        lead="Pessoa_001",
        fase_atingida="qualificacao",
    )
    result = _consolidate("S_CTX", ctx, {}, 1.0, {})
    
    assert isinstance(result["contexto"], dict)
    assert result["contexto"]["consultor"] == "Beatriz"


def test_consolidate_with_pydantic_criteria():
    """Testa que CriterionResult Pydantic é convertido corretamente."""
    from agents.models import CriterionResult
    
    raw_criteria = {
        "C01": CriterionResult(nota=9.0, justificativa="Ótima saudação."),
    }
    result = _consolidate("S_PYD", {}, raw_criteria, 1.0, {})
    
    assert result["avaliacao"]["C01"]["nota"] == 9.0
    assert result["avaliacao"]["C01"]["nota_ponderada"] == 0.72  # 9 * 0.08


def test_weights_sum_to_one():
    """Garante que os pesos dos critérios somam exatamente 1.0."""
    total = sum(c["weight"] for c in CRITERIA.values())
    assert abs(total - 1.0) < 0.001


def test_highlights_derivation():
    """Testa derivação de pontos fortes e fracos."""
    raw_criteria = {
        "C01": {"nota": 10.0, "justificativa": "Saudação perfeita. Usou nome e empresa."},
        "C02": {"nota": 3.0, "justificativa": "Não qualificou o lead. Seguiu direto."},
        "C03": {"nota": 9.0, "justificativa": "Recomendação aderente. Conectou perfil."},
        "C04": {"nota": 5.0, "justificativa": "Parcial. Não tratou objeção de preço."},
        "C05": {"nota": 8.0, "justificativa": "Clara e objetiva. Linguagem adequada."},
        "C06": {"nota": 4.0, "justificativa": "Sem CTA definido. Encerrou abrupto."},
        "C07": {"nota": 10.0, "justificativa": "Conformidade total. Procedimentos ok."},
    }
    result = _consolidate("S_HL", {}, raw_criteria, 1.0, {})
    
    assert len(result["pontos_fortes"]) > 0
    assert len(result["pontos_de_melhoria"]) > 0


def test_scalability_constants():
    """Verifica que as constantes de escalabilidade estão definidas."""
    assert MAX_RETRIES >= 1
    assert RETRY_BASE_DELAY > 0
