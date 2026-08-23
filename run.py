"""
Ponto de entrada unico para rodar o servidor.

Use SEMPRE este arquivo (python run.py), ou o comando equivalente:
    uvicorn backend.main:app --reload

NAO rode "uvicorn backend.api.routes:app" -- esse modulo so tem um
`router` (APIRouter), nao um `app` (FastAPI). O `app` completo, com
CORS e o front-end montado, esta em backend/main.py.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
