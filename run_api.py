"""
Entry point para o RAG Microservice (FastAPI + Uvicorn).

Uso:
    python run_api.py
    RUN_WORKER=1 python run_api.py  # Com queue worker
"""

import uvicorn

from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True,
    )
