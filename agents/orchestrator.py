"""
Orquestrador de avaliação — async, com retry e chunking para conversas longas.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List

from agents.agents import (
    build_context_agent,
    build_sales_agent,
    build_communication_agent,
    build_process_agent,
    build_synthesis_agent,
)
import re
from agents.criteria import CRITERIA
from database import save_evaluation

logger = logging.getLogger(__name__)


def _mask_pii(text: str) -> str:
    text = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[CPF-BLOQUEADO]', text)
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL-BLOQUEADO]', text)
    text = re.sub(r'(\+?55\s?)?(\(?\d{2}\)?\s?)?9\d{4}-?\d{4}', '[TELEFONE-BLOQUEADO]', text)
    return text


MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
CHUNK_SIZE = 20

async def _run_agent_with_retry(agent, text: str, name: str, retries: int = MAX_RETRIES):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = await agent.arun(text)
            return result
        except Exception as e:
            last_error = e
            if attempt < retries:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(f"[{name}] Tentativa {attempt}/{retries} falhou: {e}. Retry em {delay}s...")
                await asyncio.sleep(delay)
    return last_error


def _chunk_conversation(text: str, messages: List[str], size: int = CHUNK_SIZE) -> List[str]:
    if len(messages) <= size:
        return [text]

    chunks = []
    for i in range(0, len(messages), size):
        chunk_msgs = messages[i:i + size]
        prefix = f"PARTE {len(chunks) + 1} DA CONVERSA:\n\n"
        chunks.append(prefix + "\n".join(chunk_msgs))
    return chunks


def _classify(nota: float) -> str:
    if nota >= 9.0: return "Excelente"
    if nota >= 7.0: return "Bom"
    if nota >= 5.0: return "Regular"
    return "Insuficiente"


def _derive_highlights(avaliacao: Dict[str, Any]) -> tuple:
    sorted_items = sorted(avaliacao.items(), key=lambda x: x[1].get("nota", 0), reverse=True)
    
    fortes = [f"{v['criterio']}: {v['justificativa'].split('.')[0]}." 
              for k, v in sorted_items if v.get("nota", 0) >= 8][:3]
    
    melhorias = [f"{v['criterio']}: {v['justificativa'].split('.')[0]}." 
                 for k, v in reversed(sorted_items) if v.get("nota", 0) < 7][:3]
                 
    return fortes, melhorias


def _consolidate(
    session_id: str,
    ctx: Optional[Any],
    results: Dict[str, Any],
    elapsed: float,
    agent_errors: Dict[str, Any],
) -> dict:
    avaliacao = {}
    nota_final = 0.0
    raw_map = {}

    def extract_from_obj(obj):
        if hasattr(obj, "model_dump"): return obj.model_dump()
        if hasattr(obj, "dict"): return obj.dict()
        return obj if isinstance(obj, dict) else {}

    if "synthesis" in results:
        syn = extract_from_obj(results["synthesis"])
        for section in ["sales", "communication", "process"]:
            sec_data = extract_from_obj(syn.get(section, {}))
            raw_map.update(sec_data)
    elif any(str(k).startswith("C0") for k in results.keys()):
        for k, v in results.items():
            raw_map[k] = extract_from_obj(v)
    else:
        for val in results.values():
            data = extract_from_obj(val)
            if any(str(k).startswith("C0") for k in data.keys()):
                raw_map.update(data)
            else:
                for sub_val in data.values():
                    sub_data = extract_from_obj(sub_val)
                    if isinstance(sub_data, dict):
                        c_keys = {k: v for k, v in sub_data.items() if str(k).startswith("C0")}
                        raw_map.update(c_keys)
                        if not c_keys and any(isinstance(v, dict) and "nota" in v for v in sub_data.values()):
                            raw_map.update(sub_data)

    for cid, criterio in CRITERIA.items():
        raw = raw_map.get(cid, {})
        if not isinstance(raw, dict): raw = {}
            
        nota = float(raw.get("nota", 0))
        nota_ponderada = round(nota * criterio["weight"], 2)
        nota_final += nota_ponderada
        avaliacao[cid] = {
            "criterio": criterio["name"],
            "peso_pct": int(criterio["weight"] * 100),
            "nota": nota,
            "nota_ponderada": nota_ponderada,
            "justificativa": str(raw.get("justificativa", "Não avaliado.")),
        }

    nota_final = round(nota_final, 2)
    fortes, melhorias = _derive_highlights(avaliacao)
    ctx_dict = extract_from_obj(ctx)

    return {
        "sessionId": session_id,
        "modelo": "gemini-2.0-flash",
        "tempo_s": elapsed,
        "is_chunked": "synthesis" in results,
        "contexto": ctx_dict,
        "avaliacao": avaliacao,
        "nota_final": nota_final,
        "classificacao": _classify(nota_final),
        "pontos_fortes": fortes,
        "pontos_de_melhoria": melhorias,
        "avisos": {k: str(v) for k, v in agent_errors.items()} if agent_errors else None
    }


async def _run_standard_eval(text: str):
    agents = [build_sales_agent(), build_communication_agent(), build_process_agent()]
    resps = await asyncio.gather(*[_run_agent_with_retry(a, text, "Agent") for a in agents])
    
    errors = {}
    valid_data = {}
    names = ["sales", "communication", "process"]
    
    for name, r in zip(names, resps):
        if isinstance(r, Exception): errors[name] = r
        else: valid_data[name] = r.content
    
    return valid_data, errors


async def evaluate_async(
    session_id: str,
    conversation_text: str,
    messages: Optional[List[str]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> dict:
    """Avalia uma conversa usando múltiplos agentes e smart chunking."""
    sem = semaphore or asyncio.Semaphore(100)
    
    async with sem:
        t0 = time.time()

        safe_conversation_text = _mask_pii(conversation_text)
        safe_messages = [_mask_pii(m) for m in (messages if messages is not None else [])]

        logger.info(f"[{session_id}] Iniciando avaliação.")

        ctx_agent = build_context_agent()
        ctx_resp = await _run_agent_with_retry(ctx_agent, safe_conversation_text, "Contexto")
        ctx_data = ctx_resp.content if not isinstance(ctx_resp, Exception) else {}

        if hasattr(ctx_data, "consultor") and ctx_data.consultor is None:
            name_match = re.search(
                r'eu sou (?:a |o )?([A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõ]+)',
                safe_conversation_text
            )
            if name_match:
                ctx_data.consultor = name_match.group(1)

        msg_list = safe_messages if safe_messages else safe_conversation_text.split("\n")
        chunks = _chunk_conversation(safe_conversation_text, msg_list)

        if len(chunks) == 1:
            results, errors = await _run_standard_eval(chunks[0])
        else:
            logger.info(f"[{session_id}] Conversa longa — usando síntese em {len(chunks)} blocos.")
            all_block_results = await asyncio.gather(*[_run_standard_eval(c) for c in chunks])

            synthesis_input = "RESUMOS DAS PARTES DA CONVERSA:\n\n"
            for i, (res, err) in enumerate(all_block_results):
                synthesis_input += f"--- BLOCO {i+1} ---\n{str(res)}\n\n"

            syn_agent = build_synthesis_agent()
            syn_resp = await _run_agent_with_retry(syn_agent, synthesis_input, "Sintetizador")

            if isinstance(syn_resp, Exception):
                results, errors = {}, {"synthesis": syn_resp}
            else:
                results = {"synthesis": syn_resp.content.model_dump()}
                errors = {}

        elapsed = round(time.time() - t0, 2)
        res = _consolidate(session_id, ctx_data, results, elapsed, errors)

        try:
            save_evaluation(res)
        except Exception as e:
            logger.error(f"Erro ao persistir avaliação no banco: {e}")
            
        return res


async def evaluate_batch_async(sessions: List[dict], format_fn, max_concurrent: int = 2) -> List[dict]:
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [evaluate_async(s["sessionId"], format_fn(s), s["messages"], semaphore) for s in sessions]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"sessionId": "N/A", "erro": str(r)} for r in results]

def evaluate(session_id: str, conversation_text: str) -> dict:
    return asyncio.run(evaluate_async(session_id, conversation_text))

def evaluate_batch(sessions: List[dict], format_fn, max_concurrent: int = 2) -> List[dict]:
    return asyncio.run(evaluate_batch_async(sessions, format_fn, max_concurrent))
