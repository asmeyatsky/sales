# Searce Scout v1.0

Autonomous AI sales agent built for Searce's GCP ecosystem. Acts as a digital SDR that researches target accounts, maps technical pain points to Searce's offerings, identifies decision-makers, executes personalized multi-channel outreach, and generates ready-to-present Google Slides decks.

## Architecture

Built with **skill2026** standards: Clean/Hexagonal Architecture, Domain-Driven Design, MCP-native integration, and parallelism-first workflows.

```
src/searce_scout/
├── shared_kernel/            # Base types, DAG orchestrator, event bus
├── account_intelligence/     # BC1: Research, signals, tech stack auditing
├── stakeholder_discovery/    # BC2: LinkedIn Sales Nav, contact validation
├── messaging/                # BC3: Personalized AI message generation
├── outreach/                 # BC4: 5-step sequence engine, inbox management
├── presentation_gen/         # BC5: Google Slides deck generation
├── crm_sync/                 # BC6: Bi-directional Salesforce/HubSpot sync
├── scout_orchestrator/       # Pipelines, DI container, settings
└── presentation/             # FastAPI API + Typer CLI
```

Each bounded context follows the same layered structure:

```
domain/          # Frozen dataclasses, value objects, events, ports (Protocols)
application/     # Commands, queries, DAG orchestration workflows, DTOs
infrastructure/  # Adapters (APIs, DB repos), MCP server
tests/           # Domain (pure), application (mocked ports), MCP compliance
```

## Searce Offerings Mapped

| Offering | Target Personas | Pain Points |
|----------|----------------|-------------|
| Cloud Migration | CTO, VP Infrastructure | Legacy debt, high on-prem costs, scalability |
| Applied AI / GenAI | Head of Innovation, CDO | Slow product cycles, manual ops, data silos |
| Data & Analytics | Head of Data, Lead Data Architect | Real-time insights, BigQuery migration |
| Future of Work | Head of HR, CIO | Remote friction, GWS adoption, collaboration gaps |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys (Vertex AI, LinkedIn, Apollo, Gmail, CRM, etc.)

# Run the CLI
scout research "Acme Corp" --website https://acme.com
scout discover <account-id> "Acme Corp"
scout outreach <account-id> --tone PROFESSIONAL_CONSULTANT
scout generate-deck <account-id> --offering "Cloud Migration"
scout pipeline "Acme Corp"          # Full end-to-end
scout weekly-batch "Company A" "Company B" "Company C"
scout check-inbox

# Start the API server
scout serve --host 0.0.0.0 --port 8000
```

## API Endpoints

All endpoints require `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/accounts/research` | Research a target account |
| GET | `/api/v1/accounts/{id}` | Get account profile |
| GET | `/api/v1/accounts/{id}/signals` | Get buying signals |
| GET | `/api/v1/accounts/migration-targets` | List high-intent migration targets |
| POST | `/api/v1/stakeholders/discover` | Discover stakeholders for account |
| POST | `/api/v1/stakeholders/{id}/validate` | Validate contact info |
| POST | `/api/v1/messages/generate` | Generate personalized message |
| POST | `/api/v1/messages/{id}/adjust-tone` | Change message tone |
| POST | `/api/v1/sequences` | Start outreach sequence |
| POST | `/api/v1/sequences/{id}/execute-step` | Execute next sequence step |
| POST | `/api/v1/sequences/{id}/stop` | Stop a sequence |
| GET | `/api/v1/sequences/active` | List active sequences |
| POST | `/api/v1/decks/generate` | Generate presentation deck |
| POST | `/api/v1/crm/push` | Push records to CRM |
| POST | `/api/v1/crm/pull` | Pull changes from CRM |
| GET | `/api/v1/crm/conflicts` | List sync conflicts |

## MCP Servers

Six MCP servers (one per bounded context) expose tools (writes) and resources (reads):

- **account-intelligence** — `research_account`, `audit_tech_stack`
- **stakeholder-discovery** — `discover_stakeholders`, `validate_contact`
- **messaging** — `generate_message`, `adjust_tone`
- **outreach** — `start_sequence`, `execute_next_step`, `process_reply`, `stop_sequence`
- **presentation** — `generate_deck`
- **crm-sync** — `push_to_crm`, `pull_from_crm`, `resolve_conflict`

## Outreach Sequence

The 5-step sequence follows a fixed order with configurable timing:

```
1. LinkedIn Connection Request  (Day 0)
2. Email 1                      (Day 2)
3. LinkedIn Message             (Day 3)
4. Email 2                      (Day 4)
5. Phone Task                   (Day 5)
```

Inbox monitoring automatically detects OOO replies (pauses sequence), "Not Interested" (stops sequence), and positive replies (stops and escalates to sales rep).

## Message Personalization

Messages are generated via Vertex AI (Gemini 1.5 Pro) with deep context:

- Buying signals detected from 10-K filings, news, and job postings
- Tech stack audit identifying competitor cloud or legacy on-prem
- Persona-matched pain points from Searce's offering catalog
- Relevant Searce case studies with concrete metrics
- Two tone modes: **Professional Consultant** or **Witty Tech Partner**

## "First Call" Deck Generation

Auto-generated Searce-branded Google Slides with:

- **The Hook** — "Why [Company] needs GCP now" based on research
- **The Gap** — Current state vs. "Futurified" state
- **Social Proof** — Matched Searce case studies by industry/offering
- **Call to Action** — Next steps for discovery call

## Testing

```bash
# Run all tests
pytest src/ tests/ -v

# Domain tests only (pure, no mocks)
pytest src/searce_scout/*/tests/domain/ -v

# Application tests (mocked ports)
pytest src/searce_scout/*/tests/application/ -v

# MCP compliance tests
pytest src/searce_scout/*/tests/mcp/ -v

# Integration tests (requires mock adapters)
pytest tests/integration/ -v -m integration

# E2E API tests
pytest tests/e2e/ -v -m e2e
```

## Tech Stack

- **AI**: Google Vertex AI (Gemini 1.5 Pro) for message generation, signal extraction, reply classification, slide content
- **API**: FastAPI with Pydantic v2 request/response models
- **CLI**: Typer
- **Database**: SQLAlchemy async (SQLite dev / PostgreSQL prod)
- **MCP**: Model Context Protocol SDK for inter-context communication
- **CRM**: Salesforce REST API, HubSpot API v3
- **Outreach**: Gmail API, LinkedIn API
- **Presentations**: Google Slides API
- **Research**: SEC EDGAR, NewsAPI, Adzuna, BuiltWith
- **Contact Enrichment**: Apollo.io, ZoomInfo

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

- `SCOUT_GCP_PROJECT_ID` — Google Cloud project for Vertex AI
- `SCOUT_LINKEDIN_API_KEY` — LinkedIn Sales Navigator API access
- `SCOUT_APOLLO_API_KEY` — Apollo.io for contact enrichment
- `SCOUT_GMAIL_CREDENTIALS_PATH` — Gmail API service account credentials
- `SCOUT_CRM_PROVIDER` — `salesforce` or `hubspot`
- `SCOUT_SLIDES_TEMPLATE_ID` — Searce-branded Google Slides template ID
- `SCOUT_API_KEY` — API authentication key

## License

MIT
