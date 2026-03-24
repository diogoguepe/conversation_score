#!/usr/bin/env python3
"""
conversation-score — CLI para pontuação de conversas de consultoria educacional.

Uso:
  python main.py --session S_27d73d98          # avalia sessão específica pelo ID
  python main.py --index 0                     # avalia sessão pelo índice (0-based)
  python main.py --all                         # avalia todas as sessões
  python main.py --list                        # lista sessões disponíveis

Opções adicionais:
  --file PATH    caminho para o arquivo de conversas (padrão: examples/conversations.json)
  --output PATH  salva o resultado em arquivo JSON (opcional)
  --verbose      exibe resposta bruta do modelo além do JSON parseado
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONVERSATIONS_FILE = Path(__file__).parent / "examples" / "conversations.json"


def load_conversations(filepath: str) -> List[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("O arquivo de conversas deve ser uma lista JSON.")
    return data


def format_conversation(session: dict) -> str:
    """Formata a sessão como texto legível para os agentes."""
    lines = [f"SESSION ID: {session['sessionId']}", ""]
    for msg in session["messages"]:
        if msg.startswith("human:"):
            lines.append(f"LEAD: {msg[len('human:'):].strip()}")
        elif msg.startswith("ai:"):
            lines.append(f"CONSULTOR: {msg[len('ai:'):].strip()}")
        else:
            lines.append(msg.strip())
    return "\n".join(lines)


def evaluate_session(session: dict, verbose: bool = False) -> dict:
    from agents import evaluate
    
    conversation_text = format_conversation(session)
    result = evaluate(session["sessionId"], conversation_text)

    if verbose:
        print("\n--- RESULTADO DA AVALIAÇÃO ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("--- FIM DO RESULTADO ---\n")

    return result


def print_result(result: dict) -> None:
    print("\n" + "=" * 70)
    print(f"  SESSION: {result.get('sessionId', 'N/A')}")
    print(f"  TEMPO  : {result.get('tempo_s', 'N/A')}s")
    print("=" * 70)

    if "erro" in result:
        print(f"ERRO: {result['erro']}")
        return

    avisos = result.get("avisos", {})
    if avisos:
        print("\n" + "!" * 70)
        print("ALERTA: FALHA NA COMUNICAÇÃO COM A API DO GEMINI")
        print("As notas podem estar zeradas porque o limite de cota foi atingido.")
        print("Verifique o campo 'avisos' no JSON de saída para detalhes técnicos.")
        print("!" * 70)
        for agent, error in avisos.items():
            print(f"  [!] Agente '{agent}': {error}")
        print("-" * 70)

    ctx = result.get("contexto", {})
    if ctx:
        print(f"\nCONSULTOR : {ctx.get('consultor', 'N/A')}")
        print(f"LEAD      : {ctx.get('lead', 'N/A')}")
        print(f"CURSO     : {ctx.get('curso_interest', 'N/A')}")
        print(f"PERFIL    : {ctx.get('perfil_lead', 'N/A')}")
        print(f"FASE      : {ctx.get('fase_atingida', 'N/A')}")

    avaliacao = result.get("avaliacao", {})
    if avaliacao:
        print(f"\n{'CRITÉRIO':<40} {'PESO':>5}  {'NOTA':>5}  {'POND.':>6}")
        print("-" * 62)
        for cid in ["C01", "C02", "C03", "C04", "C05", "C06", "C07"]:
            c = avaliacao.get(cid, {})
            nome = c.get("criterio", cid)
            peso = c.get("peso_pct", "?")
            nota = c.get("nota", "?")
            pond = c.get("nota_ponderada", "?")
            print(f"  {cid} {nome:<36} {peso:>4}%  {nota:>5}  {pond:>6}")

        print("-" * 62)
        nota_final = result.get("nota_final", "?")
        classificacao = result.get("classificacao", "")
        print(f"  {'NOTA FINAL':>38}         {nota_final:>5}  ({classificacao})")

    fortes = result.get("pontos_fortes", [])
    melhorias = result.get("pontos_de_melhoria", [])

    if fortes:
        print("\nPONTOS FORTES:")
        for p in fortes:
            print(f"  + {p}")

    if melhorias:
        print("\nPONTOS DE MELHORIA:")
        for p in melhorias:
            print(f"  - {p}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Avaliador de qualidade de conversas de consultoria educacional."
    )
    parser.add_argument("--session", help="ID da sessão a avaliar (ex: S_27d73d98)")
    parser.add_argument("--index", type=int, help="Índice da sessão (0-based)")
    parser.add_argument("--all", action="store_true", dest="all_sessions", help="Avalia todas as sessões")
    parser.add_argument("--list", action="store_true", dest="list_sessions", help="Lista sessões disponíveis")
    parser.add_argument("--file", default=str(DEFAULT_CONVERSATIONS_FILE), help="Caminho para o arquivo de conversas")
    parser.add_argument("--output", help="Salva resultado(s) em arquivo JSON")
    parser.add_argument("--verbose", action="store_true", help="Exibe resposta bruta do modelo")
    args = parser.parse_args()

    if not os.getenv("GOOGLE_API_KEY"):
        print("ERRO: GOOGLE_API_KEY não configurada. Crie um arquivo .env com base em .env.example.")
        sys.exit(1)

    conversations = load_conversations(args.file)

    if args.list_sessions:
        print(f"\nSessões disponíveis ({len(conversations)} total):\n")
        for i, s in enumerate(conversations):
            msgs = len(s["messages"])
            print(f"  [{i:2d}] {s['sessionId']}  ({msgs} mensagens)")
        print()
        return

    if args.all_sessions:
        sessions_to_eval = conversations
    elif args.session:
        sessions_to_eval = [s for s in conversations if s["sessionId"] == args.session]
        if not sessions_to_eval:
            print(f"ERRO: Sessão '{args.session}' não encontrada.")
            sys.exit(1)
    elif args.index is not None:
        if args.index >= len(conversations):
            print(f"ERRO: Índice {args.index} fora do range (0-{len(conversations)-1}).")
            sys.exit(1)
        sessions_to_eval = [conversations[args.index]]
    else:
        parser.print_help()
        sys.exit(0)

    results = []
    
    if args.all_sessions and len(sessions_to_eval) > 1:
        from agents import evaluate_batch

        print(f"\nAvaliando {len(sessions_to_eval)} sessões em lote...\n")
        results = evaluate_batch(sessions_to_eval, format_conversation)
        for result in results:
            print_result(result)
    else:
        for session in sessions_to_eval:
            print(f"\nAvaliando sessão {session['sessionId']}...")
            result = evaluate_session(session, verbose=args.verbose)
            print_result(result)
            results.append(result)

    if args.output:
        output_data = results if len(results) > 1 else results[0]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Resultado salvo em: {args.output}")


if __name__ == "__main__":
    main()
