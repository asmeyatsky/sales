"""
Presentation deck endpoints.

POST /api/v1/decks/generate              -- Generate a deck
GET  /api/v1/decks/{deck_id}             -- Get a deck
GET  /api/v1/decks/account/{account_id}  -- List decks for account
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from searce_scout.presentation_gen.application.commands.generate_deck import (
    GenerateDeckCommand,
)
from searce_scout.presentation_gen.application.queries.get_deck import GetDeckQuery
from searce_scout.presentation_gen.application.queries.list_decks_for_account import (
    ListDecksForAccountQuery,
)

from searce_scout.presentation.api.schemas.api_schemas import DeckRequest

router = APIRouter(prefix="/api/v1/decks", tags=["presentations"])


@router.post("/generate")
async def generate_deck(body: DeckRequest, request: Request) -> dict:
    """Generate a presentation deck for an account."""
    container = request.app.state.container
    cmd = GenerateDeckCommand(
        account_id=body.account_id,
        offering=body.offering,
        template_id=container.settings.slides_template_id,
    )
    # Assemble account context from the account profile
    account_context: dict = {"company_name": "", "industry": "", "tech_stack_summary": ""}
    try:
        from searce_scout.account_intelligence.application.queries.get_account_profile import (
            GetAccountProfileQuery,
        )

        profile = await container.get_account_profile_handler.execute(
            GetAccountProfileQuery(account_id=body.account_id)
        )
        if profile:
            account_context = {
                "company_name": profile.company_name,
                "industry": profile.industry_name,
                "tech_stack_summary": profile.tech_stack_summary or "",
                "migration_score": profile.migration_opportunity_score,
            }
    except Exception:
        pass

    result = await container.generate_deck_handler.execute(cmd, account_context)
    return result.model_dump()


@router.get("/account/{account_id}")
async def list_decks_for_account(account_id: str, request: Request) -> list[dict]:
    """List all decks generated for an account."""
    container = request.app.state.container
    query = ListDecksForAccountQuery(account_id=account_id)
    results = await container.list_decks_for_account_handler.execute(query)
    return [r.model_dump() for r in results]


@router.get("/{deck_id}")
async def get_deck(deck_id: str, request: Request) -> dict:
    """Get a specific deck by ID."""
    container = request.app.state.container
    query = GetDeckQuery(deck_id=deck_id)
    result = await container.get_deck_handler.execute(query)
    if result is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result.model_dump()
