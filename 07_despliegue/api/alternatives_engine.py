from .inference import score_registro
from .mcp_schemas import MCPResult, Scenario, ScoringResult, SimulationInput

CUOTAS_VALIDAS = [12, 24, 36, 48, 60]
PRINCIPAL_STEP = 5000
PRINCIPAL_MIN = 5000


def clasificar_riesgo(pe_euros: float) -> str:
    if pe_euros < 1000:
        return "bajo"
    if pe_euros < 5000:
        return "medio"
    return "alto"


def riesgo_score(nivel: str) -> int:
    return {"bajo": 0, "medio": 1, "alto": 2}[nivel]


def pe_desde_ratio(perdida_esperada: float, principal: float) -> float:
    return perdida_esperada * principal


def _variantes_principal(principal_original: float) -> list[float]:
    variantes = []
    principal = principal_original - PRINCIPAL_STEP
    while principal >= PRINCIPAL_MIN:
        variantes.append(float(principal))
        principal -= PRINCIPAL_STEP
    return variantes


def _variantes_cuotas(num_cuotas_original: int) -> list[int]:
    return [cuota for cuota in CUOTAS_VALIDAS if cuota > num_cuotas_original]


def _generar_combinaciones(original: SimulationInput) -> list[SimulationInput]:
    combinaciones: set[tuple[float, int]] = set()
    p0 = float(original.principal)
    c0 = int(original.num_cuotas)

    for principal in _variantes_principal(p0):
        combinaciones.add((principal, c0))

    for cuotas in _variantes_cuotas(c0):
        combinaciones.add((p0, cuotas))

    for principal in _variantes_principal(p0):
        for cuotas in _variantes_cuotas(c0):
            combinaciones.add((principal, cuotas))

    escenarios = []
    for principal, num_cuotas in sorted(combinaciones):
        escenarios.append(
            SimulationInput(
                id_cliente=original.id_cliente,
                principal=principal,
                tipo_interes=original.tipo_interes,
                num_cuotas=num_cuotas,
                finalidad=original.finalidad,
                vivienda=original.vivienda,
            )
        )
    return escenarios


def _evaluar_escenario(
    entrada: SimulationInput,
    principal_original: float,
    cuotas_original: int,
) -> Scenario:
    raw = score_registro(entrada.to_registro())
    pe = pe_desde_ratio(float(raw["perdida_esperada"]), float(entrada.principal))
    nivel = clasificar_riesgo(pe)
    scoring = ScoringResult(
        id_cliente=int(raw["id_cliente"]),
        score_pd=float(raw["score_pd"]),
        score_ead=float(raw["score_ead"]),
        score_lgd=float(raw["score_lgd"]),
        pe=pe,
        nivel_riesgo=nivel,
    )

    if principal_original > 0:
        pct_reduccion_principal = (principal_original - entrada.principal) / principal_original
    else:
        pct_reduccion_principal = 0.0

    if cuotas_original > 0:
        pct_aumento_cuotas = (entrada.num_cuotas - cuotas_original) / cuotas_original
    else:
        pct_aumento_cuotas = 0.0

    impacto_cambio = pct_reduccion_principal + pct_aumento_cuotas
    pe_relativa = pe / entrada.principal if entrada.principal > 0 else 0.0
    ranking = (
        0.5 * riesgo_score(nivel)
        + 0.3 * pe_relativa
        + 0.2 * impacto_cambio
    )

    return Scenario(
        input=entrada,
        scoring=scoring,
        ranking_score=ranking,
        impacto_cambio=impacto_cambio,
    )


def evaluate_loan_alternatives(case: dict) -> dict:
    original_input = SimulationInput.from_dict(case)
    principal_original = float(original_input.principal)
    cuotas_original = int(original_input.num_cuotas)

    escenario_original = _evaluar_escenario(
        original_input, principal_original, cuotas_original
    )
    pe_original = escenario_original.scoring.pe
    activar_chat = escenario_original.scoring.nivel_riesgo == "alto"

    alternativas: list[Scenario] = []
    for candidato in _generar_combinaciones(original_input):
        escenario = _evaluar_escenario(candidato, principal_original, cuotas_original)
        if escenario.scoring.nivel_riesgo == "alto":
            continue
        if escenario.scoring.pe >= pe_original:
            continue
        alternativas.append(escenario)

    alternativas.sort(key=lambda item: item.ranking_score)
    mejor = alternativas[0] if alternativas else None
    if mejor is not None:
        mejor.es_mejor = True

    resultado = MCPResult(
        escenario_original=escenario_original,
        alternativas=alternativas,
        mejor_alternativa=mejor,
        activar_chat=activar_chat,
    )
    return resultado.to_dict()
