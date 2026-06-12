import logging
from contextlib import asynccontextmanager

import sys
from unittest.mock import MagicMock
# ---------------------------------------------------------
# CRITICAL BUG FIX FOR AZURE APP SERVICE + OPENTELEMETRY
# Azure's uv installer breaks OpenTelemetry namespace packages.
# We intercept the import and provide a fake module so it doesn't crash.
# ---------------------------------------------------------
if 'opentelemetry.exporter.otlp.proto.common._exporter_metrics' not in sys.modules:
    sys.modules['opentelemetry.exporter.otlp.proto.common._exporter_metrics'] = MagicMock()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import our custom modules
from app.database import init_db
from app.search_engine import hybrid_search_engine
from app.routers import chat

# Set up logging so we can see what's happening behind the scenes
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting up the application and initializing the database...")
        # Initialize the database and create tables if they don't exist
        await init_db()
        logger.info("Database initialized successfully.")
        
        logger.info("Pre-loading Search Engine to prevent race conditions...")
        await hybrid_search_engine.initialize_engine()
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
    yield

# Create the main FastAPI application instance
app = FastAPI(title="Gluzo AI Backend", lifespan=lifespan)

# Add CORS middleware to allow requests from any origin (e.g., frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Include Routers
# ---------------------------------------------------------

app.include_router(chat.router)

# ---------------------------------------------------------
# Static Files (Product Images)
# ---------------------------------------------------------
# This makes the local product images accessible via URL.
# Example: http://localhost:8000/images/revlon-touch-and-glow-advanced-glow-cream/0.jpg
app.mount("/images", StaticFiles(directory="data/images_final"), name="images")

# ---------------------------------------------------------
# Root Endpoint (Health Check)
# ---------------------------------------------------------

@app.get("/")
async def root():
    """
    A simple endpoint to verify the server is running.
    """
    logger.info("Root endpoint was accessed.")
    return {"message": "Welcome to the Gluzo AI Backend"}
