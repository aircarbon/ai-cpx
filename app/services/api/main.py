import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import config, risk
from app.core.database import init_database
from app.core.models import (
    RiskType, RiskDimensionSpec, Project, ProjectScore, RiskAssessment, 
    Evidence, EvidenceRating, Chunk, SourceDocument
)

# Import env variables
load_dotenv()

# Global client variable for FastAPI lifecycle
db_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_client
    # Initialize database with all required models for the API service
    db_client = await init_database([
        RiskType, RiskDimensionSpec, Project, ProjectScore, RiskAssessment, 
        Evidence, EvidenceRating, Chunk, SourceDocument
    ])
    if not db_client:
        raise RuntimeError("Failed to initialize database connection")
    
    yield
    
    # Shutdown
    if db_client:
        db_client.close()

# Create an instance of the FastAPI class with enhanced OpenAPI configuration
app = FastAPI(
    title="AI CPX API",
    description="""
    A comprehensive API for carbon credit project risk assessment and analysis.
    
    This API provides endpoints to:
    * Get project risk scores and breakdowns
    * View detailed risk assessments with evidences
    * Examine evidence ratings and chunk content
    * Access configuration data for risk types and dimensions
    
    The API uses advanced AI models to analyze project documents and assess various risk factors.
    """,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "risk",
            "description": "Risk assessment and analysis endpoints",
        },
        {
            "name": "config",
            "description": "Configuration and metadata endpoints",
        },
    ]
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router)
app.include_router(risk.router)
