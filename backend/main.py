"""FastAPI app principal — Agentic Credit Agro (replica arquitetural do artigo)."""
import os

# Carrega variaveis de .env (ex.: OPENAI_API_KEY) ANTES de qualquer outro
# import do projeto, para que backend.llm.narrative_agent enxergue a chave
# mesmo quando o usuario nao exportou a variavel manualmente no shell.
# Se python-dotenv nao estiver instalado, segue sem quebrar (a chave ainda
# pode ser definida via variavel de ambiente do sistema operacional).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router

app = FastAPI(title="FarmTech — Agentic Credit Risk (Brazil)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    # Montado na raiz (nao em /static): index.html referencia css/js com
    # caminhos relativos a "/", entao o StaticFiles precisa servir a partir
    # da raiz. html=True faz "/" resolver para index.html automaticamente.
    # Isso e registrado DEPOIS do include_router(router) acima, entao
    # /api/*, /ws etc. continuam tendo prioridade sobre o catch-all estatico.
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
