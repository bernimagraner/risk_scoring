import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"
).rstrip("/")
MCP_LOCAL_DIRECT = os.getenv("MCP_LOCAL_DIRECT", "true").lower() in {
    "1",
    "true",
    "yes",
}


def _load_evaluation_direct(case: dict) -> dict:
    deploy_root = Path(__file__).resolve().parent.parent
    if str(deploy_root) not in sys.path:
        sys.path.insert(0, str(deploy_root))
    from api.alternatives_engine import evaluate_loan_alternatives

    return evaluate_loan_alternatives(case)


def _build_instructions(case: dict, scoring: dict, pe_euros: float) -> str:
    return (
        "Eres un asesor de riesgo crediticio. "
        "Debes explicar en español, de forma clara y profesional, las alternativas "
        "de préstamo disponibles para un caso de riesgo alto. "
        "No recalcules scoring ni modifiques el ranking. "
        "No inventes escenarios. Usa únicamente la información proporcionada por la tool MCP "
        "o por el resultado estructurado adjunto. "
        "Destaca la mejor alternativa, compara principal y plazo, "
        "y explica por qué reduce la pérdida esperada."
        f"\n\nCaso original:\n{json.dumps(case, ensure_ascii=False, indent=2)}"
        f"\n\nScoring original:\n{json.dumps(scoring, ensure_ascii=False, indent=2)}"
        f"\n\nPérdida esperada original en euros: {pe_euros:.2f}"
    )


def _explain_with_direct_mcp(case: dict, scoring: dict, pe_euros: float, user_message: str) -> str:
    evaluation = _load_evaluation_direct(case)
    prompt = (
        _build_instructions(case, scoring, pe_euros)
        + "\n\nResultado estructurado del servidor MCP:\n"
        + json.dumps(evaluation, ensure_ascii=False, indent=2)
        + "\n\nPregunta o petición del gestor:\n"
        + user_message
    )

    client = OpenAI()
    response = client.responses.create(
        model=DEFAULT_MODEL,
        input=prompt,
    )
    return response.output_text or "No se pudo generar una explicación."


def _explain_with_remote_mcp(case: dict, scoring: dict, pe_euros: float, user_message: str) -> str:
    client = OpenAI()
    prompt = (
        _build_instructions(case, scoring, pe_euros)
        + "\n\nConsulta el servidor MCP para obtener las alternativas válidas "
        "y responde a la petición del gestor:\n"
        + user_message
    )
    response = client.responses.create(
        model=DEFAULT_MODEL,
        tools=[
            {
                "type": "mcp",
                "server_label": "risk_scoring_mcp",
                "server_description": (
                    "Servidor MCP de scoring que genera y evalúa alternativas de préstamo."
                ),
                "server_url": MCP_SERVER_URL,
                "require_approval": "never",
                "allowed_tools": ["evaluate_loan_alternatives_tool"],
            }
        ],
        input=prompt,
    )
    return response.output_text or "No se pudo generar una explicación."


def explain_high_risk_case(
    case: dict,
    scoring: dict,
    pe_euros: float,
    user_message: str,
) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "No hay OPENAI_API_KEY configurada. "
            "Crea un archivo .env en la raíz del proyecto o exporta la variable."
        )

    try:
        if MCP_LOCAL_DIRECT:
            return _explain_with_direct_mcp(case, scoring, pe_euros, user_message)
        return _explain_with_remote_mcp(case, scoring, pe_euros, user_message)
    except Exception as exc:
        return (
            "No se pudo completar la consulta al asistente. "
            f"Detalle: {exc}"
        )
