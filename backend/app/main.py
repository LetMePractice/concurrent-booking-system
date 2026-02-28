"""
Event Booking API - Main Application Entry Point

A high-throughput event booking system demonstrating:
- Concurrency-safe seat reservation with optimistic locking
- Redis caching with intelligent invalidation
- Structured logging with request correlation
- PostgreSQL with proper indexing and connection pooling
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api.router import api_router
from app.api.middleware import RequestLoggingMiddleware
from app.services.cache_service import get_redis, close_redis, get_cache_stats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    setup_logging()
    logger = get_logger(__name__)

    logger.info(
        "application_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Initialize Redis connection
    redis_client = await get_redis()
    if redis_client:
        logger.info("redis_ready")
    else:
        logger.warning("redis_unavailable", message="Running without cache")

    yield

    # Cleanup
    await close_redis()
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="High-throughput event booking API with concurrency-safe reservations",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Routes
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and load balancers."""
    cache_stats = await get_cache_stats()
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "cache": cache_stats,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
