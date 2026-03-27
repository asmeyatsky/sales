"""
Account endpoints.

POST /api/v1/accounts/research       -- Research a new account
GET  /api/v1/accounts/{account_id}   -- Get account profile
GET  /api/v1/accounts/{account_id}/signals -- Get buying signals
GET  /api/v1/accounts/migration-targets    -- List migration targets
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from searce_scout.account_intelligence.application.commands.research_account import (
    ResearchAccountCommand,
)
from searce_scout.account_intelligence.application.queries.find_migration_targets import (
    FindMigrationTargetsQuery,
)
from searce_scout.account_intelligence.application.queries.get_account_profile import (
    GetAccountProfileQuery,
)
from searce_scout.account_intelligence.application.queries.list_buying_signals import (
    ListBuyingSignalsQuery,
)

from searce_scout.presentation.api.schemas.api_schemas import (
    ErrorResponse,
    ResearchRequest,
    ResearchResponse,
)

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.post("/research", response_model=ResearchResponse)
async def research_account(body: ResearchRequest, request: Request) -> ResearchResponse:
    """Research a new target account."""
    container = request.app.state.container
    cmd = ResearchAccountCommand(
        company_name=body.company_name,
        website=body.website,
        ticker=body.ticker,
    )
    dto = await container.research_account_handler.execute(cmd)
    return ResearchResponse(
        account_id=dto.account_id,
        company_name=dto.company_name,
        migration_score=dto.migration_opportunity_score,
        signal_count=dto.buying_signal_count,
        stakeholders_found=0,
    )


@router.get("/migration-targets")
async def list_migration_targets(
    request: Request, min_score: float = 0.7
) -> list[dict]:
    """List accounts that are migration targets above the given score."""
    container = request.app.state.container
    query = FindMigrationTargetsQuery(min_score=min_score)
    results = await container.find_migration_targets_handler.execute(query)
    return [r.model_dump() for r in results]


@router.get("/{account_id}")
async def get_account_profile(account_id: str, request: Request) -> dict:
    """Get account profile by ID."""
    container = request.app.state.container
    query = GetAccountProfileQuery(account_id=account_id)
    dto = await container.get_account_profile_handler.execute(query)
    if dto is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return dto.model_dump()


@router.get("/{account_id}/signals")
async def list_buying_signals(account_id: str, request: Request) -> list[dict]:
    """Get buying signals for an account."""
    container = request.app.state.container
    query = ListBuyingSignalsQuery(account_id=account_id)
    results = await container.list_buying_signals_handler.execute(query)
    return [r.model_dump() for r in results]
