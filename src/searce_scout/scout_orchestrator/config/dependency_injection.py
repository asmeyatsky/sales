"""
Dependency Injection Container

Creates and wires all adapters, repositories, and command/query handlers
using functools.cached_property for lazy singleton creation.  The Container
is the single composition root for the entire Searce Scout application.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.scout_orchestrator.config.settings import ScoutSettings


# ---------------------------------------------------------------------------
# In-process event bus (satisfies EventBusPort)
# ---------------------------------------------------------------------------


class InMemoryEventBus:
    """Lightweight in-process event bus for domain events."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = {}

    async def publish(self, events: tuple[DomainEvent, ...] | list[DomainEvent]) -> None:
        for event in events:
            for handler in self._handlers.get(type(event), []):
                await handler(event)

    async def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)


# ---------------------------------------------------------------------------
# DI Container
# ---------------------------------------------------------------------------


class Container:
    """Composition root that creates and wires all dependencies."""

    def __init__(self, settings: ScoutSettings) -> None:
        self.settings = settings

    # == Event Bus ==========================================================

    @functools.cached_property
    def event_bus(self) -> InMemoryEventBus:
        return InMemoryEventBus()

    # == Account Intelligence adapters ======================================

    @functools.cached_property
    def account_repository(self) -> Any:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from searce_scout.account_intelligence.infrastructure.adapters.account_repository import (
            AccountRepository,
        )

        engine = create_async_engine(self.settings.database_url, echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        return AccountRepository(session=session)

    @functools.cached_property
    def vertex_ai_analyzer(self) -> Any:
        from searce_scout.account_intelligence.infrastructure.adapters.vertex_ai_analyzer import (
            VertexAIAnalyzer,
        )

        return VertexAIAnalyzer(
            project_id=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
            model_name=self.settings.vertex_ai_model,
        )

    @functools.cached_property
    def sec_edgar_scraper(self) -> Any:
        from searce_scout.account_intelligence.infrastructure.adapters.sec_edgar_scraper import (
            SecEdgarScraper,
        )

        return SecEdgarScraper()

    @functools.cached_property
    def news_api_scraper(self) -> Any:
        from searce_scout.account_intelligence.infrastructure.adapters.news_api_scraper import (
            NewsApiScraper,
        )

        return NewsApiScraper(api_key=self.settings.apollo_api_key)

    @functools.cached_property
    def job_board_scraper(self) -> Any:
        from searce_scout.account_intelligence.infrastructure.adapters.job_board_scraper import (
            JobBoardScraper,
        )

        return JobBoardScraper(app_id="", app_key="")

    @functools.cached_property
    def builtwith_detector(self) -> Any:
        from searce_scout.account_intelligence.infrastructure.adapters.builtwith_detector import (
            BuiltWithDetector,
        )

        return BuiltWithDetector(api_key="")

    # == Stakeholder Discovery adapters =====================================

    @functools.cached_property
    def linkedin_adapter(self) -> Any:
        from searce_scout.stakeholder_discovery.infrastructure.adapters.linkedin_sales_nav_adapter import (
            LinkedInSalesNavAdapter,
        )

        return LinkedInSalesNavAdapter(
            api_key=self.settings.linkedin_api_key,
            api_secret=self.settings.linkedin_api_secret,
        )

    @functools.cached_property
    def apollo_adapter(self) -> Any:
        from searce_scout.stakeholder_discovery.infrastructure.adapters.apollo_enrichment_adapter import (
            ApolloEnrichmentAdapter,
        )

        return ApolloEnrichmentAdapter(api_key=self.settings.apollo_api_key)

    # == Messaging adapters =================================================

    @functools.cached_property
    def vertex_ai_message_generator(self) -> Any:
        from searce_scout.messaging.infrastructure.adapters.vertex_ai_message_generator import (
            VertexAIMessageGenerator,
        )

        return VertexAIMessageGenerator(
            project_id=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
            model_name=self.settings.vertex_ai_model,
        )

    @functools.cached_property
    def case_study_repository(self) -> Any:
        from searce_scout.messaging.infrastructure.adapters.case_study_repository import (
            CaseStudyRepository,
        )

        return CaseStudyRepository()

    # == Outreach adapters ==================================================

    @functools.cached_property
    def gmail_sender(self) -> Any:
        from searce_scout.outreach.infrastructure.adapters.gmail_sender import GmailSender

        return GmailSender(
            credentials_path=self.settings.gmail_credentials_path,
            sender_email=self.settings.sender_email,
        )

    @functools.cached_property
    def gmail_inbox_reader(self) -> Any:
        from searce_scout.outreach.infrastructure.adapters.gmail_inbox_reader import (
            GmailInboxReader,
        )

        return GmailInboxReader(
            credentials_path=self.settings.gmail_credentials_path,
            user_email=self.settings.sender_email,
        )

    @functools.cached_property
    def linkedin_messenger(self) -> Any:
        from searce_scout.outreach.infrastructure.adapters.linkedin_messenger import (
            LinkedInMessenger,
        )

        return LinkedInMessenger(access_token=self.settings.linkedin_api_key)

    @functools.cached_property
    def vertex_ai_classifier(self) -> Any:
        from searce_scout.outreach.infrastructure.adapters.vertex_ai_classifier import (
            VertexAIClassifier,
        )

        return VertexAIClassifier(
            project_id=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
            model_name=self.settings.vertex_ai_model,
        )

    # == Presentation Gen adapters ==========================================

    @functools.cached_property
    def google_slides_renderer(self) -> Any:
        from searce_scout.presentation_gen.infrastructure.adapters.google_slides_renderer import (
            GoogleSlidesRenderer,
        )

        return GoogleSlidesRenderer(
            credentials_path=self.settings.google_credentials_path,
        )

    # == CRM adapters =======================================================

    @functools.cached_property
    def salesforce_client(self) -> Any:
        from searce_scout.crm_sync.infrastructure.adapters.salesforce_client import (
            SalesforceClient,
        )

        return SalesforceClient(
            client_id=self.settings.salesforce_client_id,
            client_secret=self.settings.salesforce_client_secret,
            instance_url=self.settings.salesforce_instance_url,
        )

    @functools.cached_property
    def hubspot_client(self) -> Any:
        from searce_scout.crm_sync.infrastructure.adapters.hubspot_client import HubSpotClient

        return HubSpotClient(api_key=self.settings.hubspot_api_key)

    @functools.cached_property
    def crm_client(self) -> Any:
        """Dispatch to the appropriate CRM client based on crm_provider setting."""
        if self.settings.crm_provider.lower() == "hubspot":
            return self.hubspot_client
        return self.salesforce_client

    # ======================================================================
    # Handler factory methods
    # ======================================================================

    @functools.cached_property
    def research_account_handler(self) -> Any:
        from searce_scout.account_intelligence.application.commands.research_account import (
            ResearchAccountHandler,
        )

        return ResearchAccountHandler(
            filing_scraper=self.sec_edgar_scraper,
            news_scraper=self.news_api_scraper,
            job_board_scraper=self.job_board_scraper,
            tech_detector=self.builtwith_detector,
            ai_analyzer=self.vertex_ai_analyzer,
            account_repository=self.account_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def discover_stakeholders_handler(self) -> Any:
        from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
            DiscoverStakeholdersHandler,
        )
        from searce_scout.stakeholder_discovery.domain.services.persona_matching import (
            PersonaMatchingService,
        )

        return DiscoverStakeholdersHandler(
            linkedin_port=self.linkedin_adapter,
            contact_enrichment=self.apollo_adapter,
            stakeholder_repository=self._stakeholder_repository,
            event_bus=self.event_bus,
            persona_matching_service=PersonaMatchingService(),
        )

    @functools.cached_property
    def validate_contact_handler(self) -> Any:
        from searce_scout.stakeholder_discovery.application.commands.validate_contact import (
            ValidateContactHandler,
        )

        return ValidateContactHandler(
            contact_enrichment=self.apollo_adapter,
            stakeholder_repository=self._stakeholder_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def generate_message_handler(self) -> Any:
        from searce_scout.messaging.application.commands.generate_message import (
            GenerateMessageHandler,
        )
        from searce_scout.messaging.domain.services.personalization_service import (
            PersonalizationService,
        )

        return GenerateMessageHandler(
            ai_message_generator=self.vertex_ai_message_generator,
            case_study_port=self.case_study_repository,
            message_repository=self._message_repository,
            event_bus=self.event_bus,
            personalization_service=PersonalizationService(),
        )

    @functools.cached_property
    def adjust_tone_handler(self) -> Any:
        from searce_scout.messaging.application.commands.adjust_tone import AdjustToneHandler

        return AdjustToneHandler(
            ai_message_generator=self.vertex_ai_message_generator,
            message_repository=self._message_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def start_sequence_handler(self) -> Any:
        from searce_scout.outreach.application.commands.start_sequence import (
            StartSequenceHandler,
        )
        from searce_scout.outreach.domain.services.sequence_engine import (
            SequenceEngineService,
        )

        return StartSequenceHandler(
            sequence_engine=SequenceEngineService(
                step_delays_hours=tuple(self.settings.step_delays_hours),
                business_hours_start=self.settings.business_hours_start,
                business_hours_end=self.settings.business_hours_end,
            ),
            sequence_repository=self._sequence_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def execute_next_step_handler(self) -> Any:
        from searce_scout.outreach.application.commands.execute_next_step import (
            ExecuteNextStepHandler,
        )
        from searce_scout.outreach.infrastructure.adapters.crm_task_creator import (
            CRMTaskCreator,
        )

        return ExecuteNextStepHandler(
            sequence_repository=self._sequence_repository,
            message_repository=self._message_repository,
            email_sender=self.gmail_sender,
            linkedin_messenger=self.linkedin_messenger,
            task_creator=CRMTaskCreator(crm_client=self.crm_client),
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def stop_sequence_handler(self) -> Any:
        from searce_scout.outreach.application.commands.stop_sequence import (
            StopSequenceHandler,
        )

        return StopSequenceHandler(
            sequence_repository=self._sequence_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def process_reply_handler(self) -> Any:
        from searce_scout.outreach.application.commands.process_reply import (
            ProcessReplyHandler,
        )
        from searce_scout.outreach.domain.services.reply_classification_service import (
            ReplyClassificationService,
        )

        return ProcessReplyHandler(
            ai_classifier=self.vertex_ai_classifier,
            reply_classification_service=ReplyClassificationService(),
            sequence_repository=self._sequence_repository,
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def generate_deck_handler(self) -> Any:
        from searce_scout.presentation_gen.application.commands.generate_deck import (
            GenerateDeckHandler,
        )
        from searce_scout.presentation_gen.domain.services.deck_composition import (
            DeckCompositionService,
        )
        from searce_scout.presentation_gen.infrastructure.adapters.vertex_ai_content_generator import (
            VertexAIContentGenerator,
        )

        return GenerateDeckHandler(
            ai_content_generator=VertexAIContentGenerator(
                project_id=self.settings.gcp_project_id,
                location=self.settings.gcp_location,
                model_name=self.settings.vertex_ai_model,
            ),
            slide_renderer=self.google_slides_renderer,
            deck_repository=self._deck_repository,
            deck_composition_service=DeckCompositionService(),
            event_bus=self.event_bus,
        )

    @functools.cached_property
    def push_to_crm_handler(self) -> Any:
        from searce_scout.crm_sync.application.commands.push_to_crm import PushToCRMHandler
        from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService

        return PushToCRMHandler(
            crm_client=self.crm_client,
            field_mapper_service=FieldMapperService(),
            sync_log_repository=self._sync_log_repository,
            event_bus=self.event_bus,
            field_mappings=(),
        )

    @functools.cached_property
    def pull_from_crm_handler(self) -> Any:
        from searce_scout.crm_sync.application.commands.pull_from_crm import PullFromCRMHandler
        from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService

        return PullFromCRMHandler(
            crm_client=self.crm_client,
            field_mapper_service=FieldMapperService(),
            sync_log_repository=self._sync_log_repository,
            event_bus=self.event_bus,
            field_mappings=(),
        )

    @functools.cached_property
    def resolve_conflict_handler(self) -> Any:
        from searce_scout.crm_sync.application.commands.resolve_conflict import (
            ResolveConflictHandler,
        )
        from searce_scout.crm_sync.domain.services.conflict_resolution import (
            ConflictResolutionService,
        )

        return ResolveConflictHandler(
            conflict_resolution_service=ConflictResolutionService(),
            crm_client=self.crm_client,
            sync_log_repository=self._sync_log_repository,
            event_bus=self.event_bus,
        )

    # == Query handlers =====================================================

    @functools.cached_property
    def get_account_profile_handler(self) -> Any:
        from searce_scout.account_intelligence.application.queries.get_account_profile import (
            GetAccountProfileHandler,
        )

        return GetAccountProfileHandler(account_repository=self.account_repository)

    @functools.cached_property
    def list_buying_signals_handler(self) -> Any:
        from searce_scout.account_intelligence.application.queries.list_buying_signals import (
            ListBuyingSignalsHandler,
        )

        return ListBuyingSignalsHandler(account_repository=self.account_repository)

    @functools.cached_property
    def find_migration_targets_handler(self) -> Any:
        from searce_scout.account_intelligence.application.queries.find_migration_targets import (
            FindMigrationTargetsHandler,
        )

        return FindMigrationTargetsHandler(account_repository=self.account_repository)

    @functools.cached_property
    def get_stakeholders_for_account_handler(self) -> Any:
        from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
            GetStakeholdersForAccountHandler,
        )

        return GetStakeholdersForAccountHandler(
            stakeholder_repository=self._stakeholder_repository,
        )

    @functools.cached_property
    def get_message_handler(self) -> Any:
        from searce_scout.messaging.application.queries.get_message import GetMessageHandler

        return GetMessageHandler(message_repository=self._message_repository)

    @functools.cached_property
    def preview_message_handler(self) -> Any:
        from searce_scout.messaging.application.queries.preview_message import (
            PreviewMessageHandler,
        )
        from searce_scout.messaging.domain.services.personalization_service import (
            PersonalizationService,
        )

        return PreviewMessageHandler(
            ai_message_generator=self.vertex_ai_message_generator,
            case_study_port=self.case_study_repository,
            personalization_service=PersonalizationService(),
        )

    @functools.cached_property
    def get_sequence_status_handler(self) -> Any:
        from searce_scout.outreach.application.queries.get_sequence_status import (
            GetSequenceStatusHandler,
        )

        return GetSequenceStatusHandler(sequence_repository=self._sequence_repository)

    @functools.cached_property
    def list_active_sequences_handler(self) -> Any:
        from searce_scout.outreach.application.queries.list_active_sequences import (
            ListActiveSequencesHandler,
        )

        return ListActiveSequencesHandler(sequence_repository=self._sequence_repository)

    @functools.cached_property
    def get_deck_handler(self) -> Any:
        from searce_scout.presentation_gen.application.queries.get_deck import GetDeckHandler

        return GetDeckHandler(deck_repository=self._deck_repository)

    @functools.cached_property
    def list_decks_for_account_handler(self) -> Any:
        from searce_scout.presentation_gen.application.queries.list_decks_for_account import (
            ListDecksForAccountHandler,
        )

        return ListDecksForAccountHandler(deck_repository=self._deck_repository)

    @functools.cached_property
    def list_conflicts_handler(self) -> Any:
        from searce_scout.crm_sync.application.queries.list_conflicts import (
            ListConflictsHandler,
        )

        return ListConflictsHandler(sync_log_repository=self._sync_log_repository)

    # == Inbox monitoring workflow ===========================================

    @functools.cached_property
    def inbox_monitoring_workflow(self) -> Any:
        from searce_scout.outreach.application.orchestration.inbox_monitoring_workflow import (
            InboxMonitoringWorkflow,
        )
        from searce_scout.outreach.domain.services.reply_classification_service import (
            ReplyClassificationService,
        )

        return InboxMonitoringWorkflow(
            inbox_reader=self.gmail_inbox_reader,
            ai_classifier=self.vertex_ai_classifier,
            reply_classification_service=ReplyClassificationService(),
            sequence_repository=self._sequence_repository,
            event_bus=self.event_bus,
        )

    # ======================================================================
    # Private: shared repository singletons (session-scoped)
    # ======================================================================

    @functools.cached_property
    def _async_session(self) -> Any:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_async_engine(self.settings.database_url, echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return session_factory()

    @functools.cached_property
    def _stakeholder_repository(self) -> Any:
        from searce_scout.stakeholder_discovery.infrastructure.adapters.stakeholder_repository import (
            StakeholderRepository,
        )

        return StakeholderRepository(session=self._async_session)

    @functools.cached_property
    def _message_repository(self) -> Any:
        from searce_scout.messaging.infrastructure.adapters.message_repository import (
            MessageRepository,
        )

        return MessageRepository(session=self._async_session)

    @functools.cached_property
    def _sequence_repository(self) -> Any:
        from searce_scout.outreach.infrastructure.adapters.sequence_repository import (
            SequenceRepository,
        )

        return SequenceRepository(session=self._async_session)

    @functools.cached_property
    def _deck_repository(self) -> Any:
        from searce_scout.presentation_gen.infrastructure.adapters.deck_repository import (
            DeckRepository,
        )

        return DeckRepository(session=self._async_session)

    @functools.cached_property
    def _sync_log_repository(self) -> Any:
        from searce_scout.crm_sync.infrastructure.adapters.sync_log_repository import (
            SyncLogRepository,
        )

        return SyncLogRepository(session=self._async_session)
