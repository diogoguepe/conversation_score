import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from sqlmodel import Field, SQLModel, Session, create_engine, select, desc

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class Evaluation(SQLModel, table=True):
    """Tabela principal de avaliações."""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    consultor: Optional[str] = None
    lead: Optional[str] = None
    fase: Optional[str] = None
    nota_final: float
    classificacao: str
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_result(cls, result: Dict[str, Any]):
        ctx = result.get("contexto", {})
        return cls(
            session_id=result.get("sessionId", "unknown"),
            consultor=ctx.get("consultor"),
            lead=ctx.get("lead"),
            fase=ctx.get("fase_atingida"),
            nota_final=result.get("nota_final", 0.0),
            classificacao=result.get("classificacao", "N/A"),
            metadata_json=json.dumps(result, ensure_ascii=False)
        )


engine = create_engine(DATABASE_URL) if DATABASE_URL else None

def init_db():
    if engine:
        SQLModel.metadata.create_all(engine)
        print("Banco de dados inicializado.")
    else:
        print("DATABASE_URL não encontrada — persistência desativada.")

def save_evaluation(result: Dict[str, Any]):
    if not engine: return None
    try:
        with Session(engine) as session:
            obj = Evaluation.from_result(result)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj.id
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
        return None

def list_evaluations(limit: int = 100) -> List[Evaluation]:
    if not engine: return []
    with Session(engine) as session:
        statement = select(Evaluation).order_by(desc(Evaluation.created_at)).limit(limit)
        return session.exec(statement).all()

def get_consultant_stats() -> List[Dict[str, Any]]:
    if not engine: return []
    with Session(engine) as session:
        statement = select(Evaluation)
        evals = session.exec(statement).all()

        summary_map: Dict[str, Dict[str, Any]] = {}
        
        total_sessoes = len(evals)
        identificados = 0

        for e in evals:
            name = e.consultor or "Não identificado"
            if e.consultor:
                identificados += 1
            if name not in summary_map:
                summary_map[name] = {"total": 0, "soma": 0.0, "notas": [], "identificado": bool(e.consultor)}

            summary_map[name]["total"] += 1
            summary_map[name]["soma"] += e.nota_final
            summary_map[name]["notas"].append(e.nota_final)

        results = []
        for name, data in summary_map.items():
            results.append({
                "consultor": name,
                "identificado": data["identificado"],
                "atendimentos": data["total"],
                "media_nota": round(data["soma"] / data["total"], 2),
                "maior_nota": max(data["notas"]) if data["notas"] else 0,
                "menor_nota": min(data["notas"]) if data["notas"] else 0,
                "taxa_identificacao": "100%" if data["identificado"] else "0%"
            })

        taxa_geral = round((identificados / total_sessoes) * 100, 1) if total_sessoes else 0
        return {
            "resumo": {
                "total_sessoes": total_sessoes,
                "atendentes_identificados": identificados,
                "taxa_identificacao_geral": f"{taxa_geral}%"
            },
            "por_consultor": sorted(results, key=lambda x: x["media_nota"], reverse=True)
        }
