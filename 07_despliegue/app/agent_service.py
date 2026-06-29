import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://risk-scoring-api-o9ec.onrender.com"
).rstrip("/")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"{DEFAULT_API_BASE_URL}/mcp").rstrip("/")


def _use_local_direct() -> bool:
    """Modo directo solo para desarrollo local explícito (repo completo + deps API)."""
    explicit = os.getenv("MCP_LOCAL_DIRECT")
    if explicit is not None:
        return explicit.lower() in {"1", "true", "yes"}
    if os.getenv("RENDER"):
        return False
    return False


def _load_evaluation_direct(case: dict) -> dict:
    deploy_root = Path(__file__).resolve().parent.parent
    if str(deploy_root) not in sys.path:
        sys.path.insert(0, str(deploy_root))
    try:
        from api.alternatives_engine import evaluate_loan_alternatives
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Modo MCP_LOCAL_DIRECT=true requiere el repo completo y las dependencias "
            "de la API. Ejecuta: pip install -r 07_despliegue/api/requirements.txt "
            "o usa MCP_LOCAL_DIRECT=false con la API desplegada."
        ) from exc

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


def _tool_context(case: dict) -> str:
    return (
        "\n\nDebes llamar a la tool evaluate_loan_alternatives_tool con exactamente "
        "estos parámetros del caso original:\n"
        f"- id_cliente: {case['id_cliente']}\n"
        f"- principal: {case['principal']}\n"
        f"- tipo_interes: {case['tipo_interes']}\n"
        f"- num_cuotas: {case['num_cuotas']}\n"
        f"- finalidad: {case['finalidad']}\n"
        f"- vivienda: {case['vivienda']}\n"
    )


def _explain_with_direct_mcp(
    case: dict, scoring: dict, pe_euros: float, user_message: str
) -> str:
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


def _explain_with_remote_mcp(
    case: dict, scoring: dict, pe_euros: float, user_message: str
) -> str:
    client = OpenAI()
    prompt = (
        _build_instructions(case, scoring, pe_euros)
        + _tool_context(case)
        + "\nConsulta el servidor MCP para obtener las alternativas válidas "
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
            "Añádela en Render (Environment) o en el archivo .env local."
        )

    try:
        if _use_local_direct():
            return _explain_with_direct_mcp(case, scoring, pe_euros, user_message)
        return _explain_with_remote_mcp(case, scoring, pe_euros, user_message)
    except Exception as exc:
        return (
            "No se pudo completar la consulta al asistente. "
            f"Detalle: {exc}"
        )
