import pandas as pd
from pathlib import Path

from .scoring import scoring_df

DATA_PATH = Path(__file__).parent / "data" / "demo_03_riesgos.csv"

COLUMNAS_PERFIL = [
    "porc_uso_revolving",
    "ingresos_verificados",
    "antigüedad_empleo",
    "num_derogatorios",
    "dti",
    "ingresos",
    "rating",
    "num_lineas_credito",
]


def calcular_cuota_francesa(principal: float, num_cuotas: int, tipo_interes: float) -> float:
    if tipo_interes == 0:
        return principal / num_cuotas
    i = tipo_interes / 12 / 100
    return principal * (i * (1 + i) ** num_cuotas) / ((1 + i) ** num_cuotas - 1)


def formatea_num_cuotas(valor: int) -> str:
    return f" {int(valor)} months"


def _cargar_historial() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def enriquecer_registro(registro: dict) -> pd.DataFrame:
    df_entrada = pd.DataFrame([registro.copy()])
    df_hist = _cargar_historial()

    df_entrada["imp_cuota"] = calcular_cuota_francesa(
        float(registro["principal"]),
        int(registro["num_cuotas"]),
        float(registro["tipo_interes"]),
    )

    df_merged = df_entrada.merge(
        df_hist, on="id_cliente", how="left", suffixes=("", "_hist")
    )

    faltantes = [col for col in COLUMNAS_PERFIL if col not in df_merged.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas tras el merge: {faltantes}")

    for col in COLUMNAS_PERFIL:
        if df_merged[col].dtype.kind in "biufc":
            df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce").fillna(0)
        else:
            df_merged[col] = df_merged[col].fillna("desconocido")

    df_merged["principal"] = (
        pd.to_numeric(df_merged["principal"], errors="coerce").fillna(0)
    )
    df_merged["tipo_interes"] = (
        pd.to_numeric(df_merged["tipo_interes"], errors="coerce").fillna(0)
    )
    df_merged["num_cuotas"] = (
        pd.to_numeric(df_merged["num_cuotas"], errors="coerce").fillna(0).astype(int)
    )
    df_merged["num_cuotas"] = df_merged["num_cuotas"].apply(formatea_num_cuotas)

    for col in [
        "ingresos_verificados",
        "vivienda",
        "finalidad",
        "rating",
        "antigüedad_empleo",
    ]:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].fillna("desconocido").astype(str)

    return df_merged.infer_objects(copy=False)


def score_registro(registro: dict) -> dict:
    df_merged = enriquecer_registro(registro)
    df_resultado = scoring_df(df_merged)
    if df_resultado.empty:
        raise ValueError("El scoring no devolvió resultados")
    return df_resultado.iloc[0].to_dict()
