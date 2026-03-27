"""Infrastructure adapter for rendering presentations via the Google Slides API.

Implements SlideRendererPort using google-api-python-client to copy a
template presentation and populate it with Slide domain objects.  Returns
the URL of the newly-created Google Slides deck.
"""

from __future__ import annotations

import logging
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from searce_scout.shared_kernel.value_objects import URL
from searce_scout.presentation_gen.domain.ports.slide_renderer_port import (
    SlideRendererPort,
)
from searce_scout.presentation_gen.domain.value_objects.slide import Slide
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId

logger = logging.getLogger(__name__)

_SLIDES_SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSlidesRenderer:
    """Google Slides API adapter implementing :class:`SlideRendererPort`.

    Parameters
    ----------
    credentials_path:
        Path to a Google service-account JSON key file with Slides and
        Drive API access.
    """

    def __init__(self, credentials_path: str) -> None:
        self._credentials_path = credentials_path
        self._slides_service: Any | None = None
        self._drive_service: Any | None = None

    # -- SlideRendererPort interface ----------------------------------------

    async def create_from_template(
        self,
        template_id: TemplateId,
        slides: tuple[Slide, ...],
    ) -> URL:
        """Copy the template presentation and populate it with *slides*.

        Steps:
        1. Duplicate the template via the Drive API.
        2. Clear placeholder slides beyond what we need.
        3. For each :class:`Slide`, insert or update content.
        4. Return the URL of the new presentation.
        """
        slides_svc = self._get_slides_service()
        drive_svc = self._get_drive_service()

        # 1. Copy the template
        new_presentation_id = self._copy_template(
            drive_svc, template_id.google_slides_id
        )

        # 2. Read the copied presentation to learn its existing slide IDs
        presentation: dict[str, Any] = (
            slides_svc.presentations()
            .get(presentationId=new_presentation_id)
            .execute()
        )
        existing_slide_ids: list[str] = [
            s["objectId"] for s in presentation.get("slides", [])
        ]

        # 3. Build batch-update requests for each domain Slide
        requests: list[dict[str, Any]] = []

        for idx, slide in enumerate(sorted(slides, key=lambda s: s.order)):
            if idx < len(existing_slide_ids):
                # Re-use / update an existing slide
                page_id = existing_slide_ids[idx]
                requests.extend(
                    self._build_replace_requests(page_id, slide)
                )
            else:
                # Create a new blank slide and populate it
                new_page_id = f"slide_{idx}"
                requests.append(
                    {
                        "createSlide": {
                            "objectId": new_page_id,
                            "insertionIndex": idx,
                            "slideLayoutReference": {
                                "predefinedLayout": "BLANK",
                            },
                        }
                    }
                )
                requests.extend(
                    self._build_insert_requests(new_page_id, slide)
                )

        # Remove surplus template slides beyond the slides we need
        for surplus_id in existing_slide_ids[len(slides):]:
            requests.append({"deleteObject": {"objectId": surplus_id}})

        # 4. Execute batch update
        if requests:
            slides_svc.presentations().batchUpdate(
                presentationId=new_presentation_id,
                body={"requests": requests},
            ).execute()

        url = f"https://docs.google.com/presentation/d/{new_presentation_id}/edit"
        logger.info(
            "Google Slides deck created from template %s -> %s",
            template_id.google_slides_id,
            url,
        )
        return URL(value=url)

    # -- Internal helpers ---------------------------------------------------

    def _get_slides_service(self) -> Any:
        if self._slides_service is not None:
            return self._slides_service
        credentials = Credentials.from_service_account_file(
            self._credentials_path, scopes=_SLIDES_SCOPES
        )
        self._slides_service = build("slides", "v1", credentials=credentials)
        return self._slides_service

    def _get_drive_service(self) -> Any:
        if self._drive_service is not None:
            return self._drive_service
        credentials = Credentials.from_service_account_file(
            self._credentials_path, scopes=_SLIDES_SCOPES
        )
        self._drive_service = build("drive", "v3", credentials=credentials)
        return self._drive_service

    @staticmethod
    def _copy_template(drive_service: Any, template_file_id: str) -> str:
        """Copy the template presentation via the Drive API and return the new file ID."""
        copy_metadata: dict[str, str] = {
            "name": f"Generated Deck (from {template_file_id})",
        }
        copied: dict[str, Any] = (
            drive_service.files()
            .copy(fileId=template_file_id, body=copy_metadata)
            .execute()
        )
        return copied["id"]

    @staticmethod
    def _build_replace_requests(
        page_id: str, slide: Slide
    ) -> list[dict[str, Any]]:
        """Build Slides API requests to replace placeholders on an existing page."""
        return [
            {
                "replaceAllText": {
                    "containsText": {"text": "{{TITLE}}", "matchCase": False},
                    "replaceText": slide.title,
                    "pageObjectIds": [page_id],
                }
            },
            {
                "replaceAllText": {
                    "containsText": {"text": "{{BODY}}", "matchCase": False},
                    "replaceText": slide.body,
                    "pageObjectIds": [page_id],
                }
            },
            {
                "replaceAllText": {
                    "containsText": {"text": "{{SPEAKER_NOTES}}", "matchCase": False},
                    "replaceText": slide.speaker_notes,
                    "pageObjectIds": [page_id],
                }
            },
        ]

    @staticmethod
    def _build_insert_requests(
        page_id: str, slide: Slide
    ) -> list[dict[str, Any]]:
        """Build Slides API requests to insert text boxes on a new blank page."""
        title_box_id = f"{page_id}_title"
        body_box_id = f"{page_id}_body"

        return [
            # Title text box
            {
                "createShape": {
                    "objectId": title_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": page_id,
                        "size": {
                            "width": {"magnitude": 600, "unit": "PT"},
                            "height": {"magnitude": 50, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 50,
                            "translateY": 30,
                            "unit": "PT",
                        },
                    },
                }
            },
            {
                "insertText": {
                    "objectId": title_box_id,
                    "text": slide.title,
                    "insertionIndex": 0,
                }
            },
            # Body text box
            {
                "createShape": {
                    "objectId": body_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": page_id,
                        "size": {
                            "width": {"magnitude": 600, "unit": "PT"},
                            "height": {"magnitude": 300, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 50,
                            "translateY": 100,
                            "unit": "PT",
                        },
                    },
                }
            },
            {
                "insertText": {
                    "objectId": body_box_id,
                    "text": slide.body,
                    "insertionIndex": 0,
                }
            },
        ]


# Structural compatibility check with the port Protocol.
_check: type[SlideRendererPort] = GoogleSlidesRenderer  # type: ignore[assignment]
