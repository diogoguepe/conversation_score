"""
Testes do main.py — formatação e carregamento de dados.
"""
import json
import tempfile
import pytest

# Importa direto para testar sem efeitos colaterais
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import format_conversation, load_conversations


def test_format_conversation():
    session = {
        "sessionId": "S_TEST",
        "messages": [
            "human: Olá, tenho interesse na pós.",
            "ai: Olá! Sou a Beatriz, consultora.",
            "human: Quero saber sobre MBA.",
        ]
    }
    text = format_conversation(session)
    assert "SESSION ID: S_TEST" in text
    assert "LEAD: Olá, tenho interesse na pós." in text
    assert "CONSULTOR: Olá! Sou a Beatriz, consultora." in text


def test_format_conversation_unknown_prefix():
    """Mensagens sem prefixo human:/ai: devem ser mantidas."""
    session = {
        "sessionId": "S_UNK",
        "messages": ["system: início da conversa"]
    }
    text = format_conversation(session)
    assert "sistema: início da conversa" in text or "system: início da conversa" in text


def test_load_conversations_valid():
    data = [{"sessionId": "S1", "messages": ["human: oi"]}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = load_conversations(f.name)
    assert len(result) == 1
    assert result[0]["sessionId"] == "S1"
    os.unlink(f.name)


def test_load_conversations_invalid():
    """Deve levantar ValueError se o JSON não for uma lista."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"not": "a list"}, f)
        f.flush()
        with pytest.raises(ValueError):
            load_conversations(f.name)
    os.unlink(f.name)
