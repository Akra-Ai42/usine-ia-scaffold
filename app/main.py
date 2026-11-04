import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.adapters import db
from app.core.schemas import ChatRequest, ChatResponse, ReviewRequest, ReviewResponse
from app.core.services import chat, guardrail

load_dotenv()

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Vigie SOC", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(_STATIC / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "Message vide")
    try:
        return await chat.analyze(req.message)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur interne : {e}")


@app.post("/api/incidents/{incident_id}/review", response_model=ReviewResponse)
async def api_review(incident_id: int, req: ReviewRequest):
    try:
        return guardrail.review(incident_id, req)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/incidents")
async def api_list_incidents():
    return JSONResponse(db.list_incidents())


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "vigie"}
