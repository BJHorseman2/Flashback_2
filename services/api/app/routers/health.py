"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    return {"status": "ready"}
