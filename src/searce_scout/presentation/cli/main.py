"""
Typer CLI application for Searce Scout.

Provides commands for research, stakeholder discovery, outreach,
deck generation, full pipeline execution, weekly batch, inbox monitoring,
and serving the API.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import typer

app = typer.Typer(
    name="scout",
    help="Searce Scout - Autonomous AI Sales Agent",
)


def _get_container():  # type: ignore[no-untyped-def]
    """Create a Container with settings loaded from environment."""
    from searce_scout.scout_orchestrator.config.dependency_injection import Container
    from searce_scout.scout_orchestrator.config.settings import ScoutSettings

    settings = ScoutSettings()
    return Container(settings)


def _get_agent():  # type: ignore[no-untyped-def]
    """Create a ScoutAgent wired with environment settings."""
    from searce_scout.scout_orchestrator.agent.scout_agent import ScoutAgent

    container = _get_container()
    return ScoutAgent(container)


def _print_json(data: object) -> None:
    """Pretty-print a dict or list as JSON."""
    typer.echo(json.dumps(data, indent=2, default=str))


@app.command()
def research(
    company_name: str = typer.Argument(..., help="Name of the company to research"),
    website: Optional[str] = typer.Option(None, help="Company website URL"),
    ticker: Optional[str] = typer.Option(None, help="Stock ticker symbol"),
) -> None:
    """Research a target account."""
    from searce_scout.account_intelligence.application.commands.research_account import (
        ResearchAccountCommand,
    )

    container = _get_container()

    async def _run() -> None:
        cmd = ResearchAccountCommand(
            company_name=company_name,
            website=website,
            ticker=ticker,
        )
        result = await container.research_account_handler.execute(cmd)
        _print_json(result.model_dump())

    asyncio.run(_run())


@app.command()
def discover(
    account_id: str = typer.Argument(..., help="Account ID"),
    company_name: str = typer.Argument(..., help="Company name"),
) -> None:
    """Discover stakeholders for an account."""
    from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
        DiscoverStakeholdersCommand,
    )

    container = _get_container()

    async def _run() -> None:
        cmd = DiscoverStakeholdersCommand(
            account_id=account_id,
            company_name=company_name,
        )
        results = await container.discover_stakeholders_handler.execute(cmd)
        _print_json([r.model_dump() for r in results])

    asyncio.run(_run())


@app.command()
def outreach(
    account_id: str = typer.Argument(..., help="Account ID"),
    tone: str = typer.Option("PROFESSIONAL_CONSULTANT", help="Message tone"),
) -> None:
    """Start outreach campaign for an account."""
    typer.echo(f"Starting outreach for account {account_id} with tone {tone}...")

    container = _get_container()

    async def _run() -> None:
        # List stakeholders for the account
        from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
            GetStakeholdersForAccountQuery,
        )

        query = GetStakeholdersForAccountQuery(account_id=account_id)
        stakeholders = await container.get_stakeholders_for_account_handler.execute(query)
        typer.echo(f"Found {len(stakeholders)} stakeholders. Starting sequences...")

        for s in stakeholders:
            typer.echo(f"  - {s.full_name} ({s.job_title})")

    asyncio.run(_run())


@app.command()
def generate_deck(
    account_id: str = typer.Argument(..., help="Account ID"),
    offering: Optional[str] = typer.Option(None, help="Searce offering to focus on"),
) -> None:
    """Generate a presentation deck."""
    from searce_scout.presentation_gen.application.commands.generate_deck import (
        GenerateDeckCommand,
    )

    container = _get_container()

    async def _run() -> None:
        cmd = GenerateDeckCommand(
            account_id=account_id,
            offering=offering,
            template_id=container.settings.slides_template_id,
        )
        account_context: dict = {
            "company_name": "",
            "industry": "",
            "tech_stack_summary": "",
        }

        # Try to load account context
        try:
            from searce_scout.account_intelligence.application.queries.get_account_profile import (
                GetAccountProfileQuery,
            )

            profile = await container.get_account_profile_handler.execute(
                GetAccountProfileQuery(account_id=account_id)
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
        _print_json(result.model_dump())

    asyncio.run(_run())


@app.command()
def pipeline(
    company_name: str = typer.Argument(..., help="Company to run the full pipeline for"),
    website: Optional[str] = typer.Option(None, help="Company website URL"),
    ticker: Optional[str] = typer.Option(None, help="Stock ticker symbol"),
    tone: str = typer.Option("PROFESSIONAL_CONSULTANT", help="Message tone"),
) -> None:
    """Run full pipeline: research -> discover -> outreach -> deck -> CRM sync."""
    agent = _get_agent()

    async def _run() -> None:
        result = await agent.research_and_outreach(
            company_name=company_name,
            website=website,
            ticker=ticker,
            tone=tone,
        )
        _print_json(result)

    typer.echo(f"Running full pipeline for {company_name}...")
    asyncio.run(_run())
    typer.echo("Pipeline complete.")


@app.command()
def weekly_batch(
    companies: list[str] = typer.Argument(..., help="Company names to research"),
    max_results: int = typer.Option(10, help="Maximum number of results"),
) -> None:
    """Run weekly research batch for multiple companies."""
    agent = _get_agent()

    async def _run() -> None:
        results = await agent.weekly_discovery(
            company_names=companies,
            max_results=max_results,
        )
        _print_json(results)

    typer.echo(f"Researching {len(companies)} companies...")
    asyncio.run(_run())
    typer.echo("Batch complete.")


@app.command()
def check_inbox() -> None:
    """Check inbox for replies and process them."""
    agent = _get_agent()

    async def _run() -> None:
        result = await agent.check_inbox_and_respond()
        _print_json(result)

    typer.echo("Checking inbox for replies...")
    asyncio.run(_run())
    typer.echo("Inbox check complete.")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
) -> None:
    """Start the API server."""
    import uvicorn

    typer.echo(f"Starting Searce Scout API on {host}:{port}...")
    uvicorn.run(
        "searce_scout.presentation.api.app:create_app",
        host=host,
        port=port,
        factory=True,
    )
