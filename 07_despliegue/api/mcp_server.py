from mcp.server.fastmcp import FastMCP

from .alternatives_engine import evaluate_loan_alternatives

mcp = FastMCP(
    "risk-scoring-mcp",
    instructions=(
        "Servidor MCP de scoring de riesgo crediticio. "
        "Genera y evalúa escenarios alternativos de préstamo."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


@mcp.tool()
def evaluate_loan_alternatives_tool(
    id_cliente: int,
    principal: float,
    tipo_interes: float,
    num_cuotas: int,
    finalidad: str,
    vivienda: str,
) -> dict:
    """Simula, evalúa, filtra y ordena alternativas de préstamo.

    Solo modifica principal y num_cuotas. Devuelve el escenario original,
    las alternativas válidas ordenadas y la mejor opción.
    """
    return evaluate_loan_alternatives(
        {
            "id_cliente": id_cliente,
            "principal": principal,
            "tipo_interes": tipo_interes,
            "num_cuotas": num_cuotas,
            "finalidad": finalidad,
            "vivienda": vivienda,
        }
    )
