from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from .schemas import LoteEntrada, ScoringSalida
from .inference import score_registro
from .mcp_server import mcp

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="API Scoring Riesgos", lifespan=lifespan)

# Servidor MCP en /mcp (Streamable HTTP, stateless para OpenAI)
app.mount("/mcp", mcp_app)


@app.post("/predict", response_model=list[ScoringSalida])
def predict(lote: LoteEntrada):
    resultados = []
    for registro in lote.root:
        try:
            resultados.append(score_registro(registro.model_dump()))
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error en inferencia: {exc}"
            ) from exc
    return resultados


@app.get("/health")
def health():
    return {"status": "ok"}
