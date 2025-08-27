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

# Create an instance of the FastAPI class
app = FastAPI(lifespan=lifespan)

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

# Endpoints
@app.get("/")
async def read_root():
    return {"message": "Test"}
