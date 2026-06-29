from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SimulationInput:
    id_cliente: int
    principal: float
    tipo_interes: float
    num_cuotas: int
    finalidad: str
    vivienda: str

    def to_registro(self) -> dict[str, Any]:
        return {
            "id_cliente": self.id_cliente,
            "principal": self.principal,
            "tipo_interes": self.tipo_interes,
            "num_cuotas": self.num_cuotas,
            "finalidad": self.finalidad,
            "vivienda": self.vivienda,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationInput":
        return cls(
            id_cliente=int(data["id_cliente"]),
            principal=float(data["principal"]),
            tipo_interes=float(data["tipo_interes"]),
            num_cuotas=int(data["num_cuotas"]),
            finalidad=str(data["finalidad"]),
            vivienda=str(data["vivienda"]),
        )


@dataclass
class ScoringResult:
    id_cliente: int
    score_pd: float
    score_ead: float
    score_lgd: float
    pe: float
    nivel_riesgo: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scenario:
    input: SimulationInput
    scoring: ScoringResult
    ranking_score: float = 0.0
    impacto_cambio: float = 0.0
    es_mejor: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input.to_registro(),
            "scoring": self.scoring.to_dict(),
            "ranking_score": self.ranking_score,
            "impacto_cambio": self.impacto_cambio,
            "es_mejor": self.es_mejor,
        }


@dataclass
class MCPResult:
    escenario_original: Scenario
    alternativas: list[Scenario] = field(default_factory=list)
    mejor_alternativa: Scenario | None = None
    activar_chat: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "escenario_original": self.escenario_original.to_dict(),
            "alternativas": [alt.to_dict() for alt in self.alternativas],
            "mejor_alternativa": (
                self.mejor_alternativa.to_dict() if self.mejor_alternativa else None
            ),
            "activar_chat": self.activar_chat,
        }
