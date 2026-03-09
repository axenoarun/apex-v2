import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router

app = FastAPI(
    title="APEX",
    description="Intelligent Delivery Operating System for AA-to-CJA Migration",
    version="2.0.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve frontend static files if dist exists (production mode)
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")


@app.get("/health")
async def health():
    """Health check endpoint for load balancers and monitoring."""
    from app.config import settings
    return {
        "status": "ok",
        "version": "2.0.0",
        "model": settings.CLAUDE_MODEL,
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
