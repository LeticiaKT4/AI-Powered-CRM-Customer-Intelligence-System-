"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analysis, customers, health, metrics, records
from services.crm_ingest import get_ingest_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_ingest_service()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AI CRM Dashboard API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
    app.include_router(records.router, prefix="/api/v1", tags=["records"])
    app.include_router(customers.router, prefix="/api/v1", tags=["customers"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    return app


app = create_app()
