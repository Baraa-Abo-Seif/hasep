import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.database.session import init_db
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.processing import router as processing_router
from backend.app.api.v1.review import router as review_router
from backend.app.api.v1.history import router as history_router
from backend.app.api.v1.financial_forms import router as financial_forms_router
from backend.app.api.v1.google_auth import router as google_auth_router
from backend.app.api.v1.google_sheets import router as google_sheets_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
)
logger = logging.getLogger("arabic_excel_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database and storage paths."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    
    # Ensure storage subdirectories exist
    for sub in ["uploads", "processed", "exports"]:
        os.makedirs(os.path.join(settings.STORAGE_DIR, sub), exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database schemas verified and initialized.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Arabic document understanding and automated Excel data entry platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local storage for serving image uploads and previews
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

# Health check
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }

# Register API v1 routers
API_V1_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(financial_forms_router, prefix=API_V1_PREFIX)
app.include_router(documents_router, prefix=API_V1_PREFIX)
app.include_router(processing_router, prefix=API_V1_PREFIX)
app.include_router(review_router, prefix=API_V1_PREFIX)
app.include_router(history_router, prefix=API_V1_PREFIX)
app.include_router(google_auth_router, prefix=API_V1_PREFIX)
app.include_router(google_sheets_router, prefix=API_V1_PREFIX)
