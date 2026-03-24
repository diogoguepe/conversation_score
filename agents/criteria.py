"""
Critérios de avaliação de qualidade para conversas de consultoria educacional.
Soma dos pesos = 100%.
"""

CRITERIA = {
    "C01": {
        "name": "Saudação e Apresentação",
        "weight": 0.08,
        "description": (
            "O consultor se apresentou com nome, empresa e objetivo da conversa "
            "de forma clara, profissional e acolhedora logo no início da interação."
        ),
        "rubric": {
            "0-3": "Ausência de apresentação ou apresentação completamente inadequada.",
            "4-6": "Apresentação parcial — faltou nome, empresa ou contexto.",
            "7-8": "Apresentação clara com nome e empresa mencionados.",
            "9-10": "Apresentação completa, profissional, acolhedora e contextualizada.",
        },
    },
    "C02": {
        "name": "Qualificação do Lead",
        "weight": 0.20,
        "description": (
            "O consultor investigou o perfil profissional do lead: formação, área de atuação, "
            "momento de carreira e objetivos com a pós-graduação antes de recomendar um curso."
        ),
        "rubric": {
            "0-3": "Não qualificou ou fez apenas uma pergunta superficial sem aprofundamento.",
            "4-6": "Qualificação parcial — cobriu algumas dimensões, mas faltaram informações-chave.",
            "7-8": "Qualificação adequada, cobrindo perfil e objetivos principais.",
            "9-10": "Qualificação completa, fluida e contextualizada em todas as dimensões relevantes.",
        },
    },
    "C03": {
        "name": "Aderência da Recomendação",
        "weight": 0.20,
        "description": (
            "O curso recomendado foi diretamente alinhado ao perfil, objetivos e necessidades "
            "identificados durante a qualificação do lead. A justificativa da recomendação foi clara."
        ),
        "rubric": {
            "0-3": "Recomendação genérica, sem conexão com o perfil identificado.",
            "4-6": "Recomendação parcialmente alinhada, com justificativa fraca.",
            "7-8": "Recomendação bem fundamentada no perfil do lead.",
            "9-10": "Recomendação precisa com justificativa personalizada e convincente.",
        },
    },
    "C04": {
        "name": "Gestão de Dúvidas e Objeções",
        "weight": 0.18,
        "description": (
            "O consultor respondeu dúvidas e objeções com segurança, clareza e sem esquivar-se. "
            "Tratou objeções como oportunidade de qualificação ou avanço na conversa."
        ),
        "rubric": {
            "0-3": "Ignorou dúvidas, deu respostas evasivas ou demonstrou insegurança.",
            "4-6": "Respondeu parcialmente, com lacunas ou inconsistências.",
            "7-8": "Respondeu bem à maioria das dúvidas com clareza.",
            "9-10": "Gestão excelente — transformou objeções em argumentos de valor.",
        },
    },
    "C05": {
        "name": "Clareza e Objetividade",
        "weight": 0.12,
        "description": (
            "As mensagens foram claras, objetivas e com linguagem adequada ao perfil do lead. "
            "Sem excesso de informação, jargões desnecessários ou ambiguidades."
        ),
        "rubric": {
            "0-3": "Comunicação confusa, verbosa, repleta de jargões ou inadequada.",
            "4-6": "Clareza razoável, mas com excessos ou ambiguidades relevantes.",
            "7-8": "Comunicação clara e adequada ao contexto.",
            "9-10": "Comunicação exemplar — precisa, adaptada ao lead e sem ruído.",
        },
    },
    "C06": {
        "name": "Encerramento e Próximos Passos",
        "weight": 0.12,
        "description": (
            "O consultor definiu próximos passos concretos, tentou avançar para matrícula "
            "ou encaminhou para especialista de forma clara e com senso de urgência adequado."
        ),
        "rubric": {
            "0-3": "Sem CTA, encerramento abrupto ou sem direcionamento.",
            "4-6": "CTA fraco ou próximos passos vagos e sem comprometimento.",
            "7-8": "CTA claro com direcionamento definido.",
            "9-10": "Encerramento excelente com urgência adequada e próximos passos detalhados.",
        },
    },
    "C07": {
        "name": "Conformidade Operacional",
        "weight": 0.10,
        "description": (
            "Respeito aos limites operacionais: não informar preços diretamente (encaminhar para "
            "especialista), tratar dados sensíveis com cuidado (LGPD), seguir fluxo estabelecido."
        ),
        "rubric": {
            "0-3": "Violações claras de procedimento ou dados sensíveis expostos.",
            "4-6": "Desvios pontuais das normas operacionais.",
            "7-8": "Conformidade adequada na maioria dos pontos críticos.",
            "9-10": "Conformidade total — todos os procedimentos seguidos exemplarmente.",
        },
    },
}

CRITERIA_IDS = list(CRITERIA.keys())
TOTAL_WEIGHT = sum(c["weight"] for c in CRITERIA.values())

assert abs(TOTAL_WEIGHT - 1.0) < 0.001, f"Soma dos pesos deve ser 1.0, got {TOTAL_WEIGHT}"
