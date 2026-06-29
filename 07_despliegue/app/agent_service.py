import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://risk-scoring-api-o9ec.onrender.com"
).rstrip("/")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"{DEFAULT_API_BASE_URL}/mcp").rstrip("/")


def _build_instructions(case: dict, scoring: dict, pe_euros: float) -> str:
    return (
        "Eres un asesor de riesgo crediticio. "
        "Debes explicar en español, de forma clara y profesional, las alternativas "
        "de préstamo disponibles para un caso de riesgo alto. "
        "No recalcules scoring ni modifiques el ranking. "
        "No inventes escenarios. Usa únicamente la información proporcionada por la tool MCP. "
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

    client = OpenAI()
    prompt = (
        _build_instructions(case, scoring, pe_euros)
        + _tool_context(case)
        + "\nConsulta el servidor MCP para obtener las alternativas válidas "
        "y responde a la petición del gestor:\n"
        + user_message
    )

    try:
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
    except Exception as exc:
        return (
            "No se pudo completar la consulta al asistente. "
            f"Detalle: {exc}\n\n"
            f"MCP en uso: {MCP_SERVER_URL}"
        )
