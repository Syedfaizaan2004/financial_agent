"""
backend/api/routes/health.py

Health-check route for the Financial & Market Research Agent API.

Used by load balancers, container orchestrators (e.g. Kubernetes), and
monitoring tools to confirm the service is running and reachable.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health Check",
    description="Returns a simple OK status to confirm the API is alive.",
    response_description="Service health status",
)
async def health_check() -> dict:
    """
    GET /health

    Returns:
        dict: {"status": "ok"} when the service is healthy.
    """
    return {"status": "ok"}
