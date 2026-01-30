"""
Corvino - FastAPI application.
Trading signals API: signals CRUD, generation trigger, health.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from api.routes import signals, health, generate, ml_train, prices, config_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    init_db()
    yield
    # shutdown if needed


app = FastAPI(
    title="Corvino",
    description="Crypto trading signals API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(signals.router, prefix="/api/signals")
app.include_router(generate.router, prefix="/api")
app.include_router(ml_train.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(config_endpoint.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "Corvino", "docs": "/docs"}
