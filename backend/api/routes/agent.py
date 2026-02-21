"""
backend/api/routes/agent.py

AI Research Agent API endpoint.

Endpoint:
    POST /agent

Accepts a natural-language research query and routes it through the
agent orchestrator (intent detection → workflow selection → synthesis).
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["AI Research Agent"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    """Request body for the agent endpoint."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural-language research query. Include a stock ticker.",
        examples=[
            "Quick summary of Apple",
            "Deep analysis of TSLA including risks and peers",
            "What happens to AAPL in a recession?",
            "Compare MSFT against competitors",
        ],
    )
    mode: str = Field(
        default="quick",
        description="Research mode: quick or deep",
    )
    analysis_type: Optional[str] = Field(
        default=None,
        description="Specific analysis type override (e.g., compare, bullbear, hidden_risks)",
    )
    scenario: Optional[str] = Field(
        default=None,
        description=(
            "Optional: override the scenario for stress testing. "
            "One of: high_inflation, recession, rate_hike, growth_slowdown"
        ),
    )
    user_id: Optional[str] = Field(
        default="default",
        max_length=64,
        description="Optional user identifier for personalized research output.",
        examples=["user_001", "analyst_A"],
    )

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be blank.")
        return v.strip()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="AI Research Agent",
    description=(
        "Accepts a natural-language research query and returns structured "
        "financial insights orchestrated by the AI Research Agent.\n\n"
        "**Workflow routing** (automatic, based on keywords):\n"
        "- `quick_research` — fast fundamentals + risk summary\n"
        "- `deep_research` — full 5-tool analysis (forecast, fundamentals, risk, peers, scenario)\n"
        "- `compare_peers` — peer comparison focus\n"
        "- `scenario_stress` — macro scenario stress focus\n"
        "- `forecast_only` — price direction forecast focus\n\n"
        "Returns **400** for empty/invalid queries.\n"
        "Returns **422** if the request body is malformed.\n"
        "Returns **500** if the agent crashes unexpectedly.\n\n"
        "**Note**: If the query contains no recognisable ticker, the response "
        "will have status='failed' and an informative error message."
    ),
    response_description="Structured AI agent research report with insights, raw data, and metadata",
)
async def run_agent(body: AgentRequest) -> Dict[str, Any]:
    """
    POST /agent

    Runs the full agent pipeline:
      1. Intent detection (keyword-based)
      2. Ticker extraction (regex-based)
      3. Workflow routing
      4. Tool orchestration
      5. Insight synthesis

    The response always has a `status` field:
      - 'ok'      — all tools ran successfully
      - 'partial' — some tools failed but results available
      - 'failed'  — no results (e.g. ticker not found in query)

    Args:
        body (AgentRequest): Request body with 'query' and optional 'scenario'.

    Returns:
        dict: Full agent response.
    """
    logger.info("[POST /agent] query='%.100s'", body.query)

    # Override scenario in query if provided explicitly
    query = body.query
    if body.scenario:
        query = f"{query} {body.scenario}"

    try:
        from backend.agent.agent import run_research_agent
        result = run_research_agent(
            query, 
            user_id=body.user_id or "default",
            mode=body.mode,
            analysis_type=body.analysis_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("[POST /agent] Unexpected agent error")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "[POST /agent] Completed | ticker=%s | intent=%s | status=%s",
        result.get("ticker"), result.get("intent"), result.get("status"),
    )
    return result
