"""
Main application entry point for RAG Application
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers (to be implemented)
# from src.api.routes import chat, documents, auth, health

# Application metadata
APP_NAME = os.getenv("APP_NAME", "RAG Application")
APP_VERSION = os.getenv("API_VERSION", "v1")
APP_DESCRIPTION = """
RAG Application with Chatbot & iOS API

This API provides endpoints for:
- Document upload and processing
- Chat with RAG-powered responses
- Authentication and user management
- iOS app integration
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    print(f"Starting {APP_NAME} {APP_VERSION}...")
    # Initialize database connections
    # Initialize vector store
    # Load models if needed
    yield
    # Shutdown
    print(f"Shutting down {APP_NAME}...")
    # Close database connections
    # Cleanup resources

# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": APP_NAME,
            "version": APP_VERSION
        }
    )

# API routes (to be implemented)
# app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
# app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    # Development server
    port = int(os.getenv("APP_PORT", 8000))
    host = os.getenv("APP_HOST", "0.0.0.0")
    reload = os.getenv("HOT_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )