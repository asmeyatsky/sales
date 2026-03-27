"""
SlideRendererPort — output port for rendering slides to a presentation platform.
"""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.value_objects import URL

from searce_scout.presentation_gen.domain.value_objects.slide import Slide
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


class SlideRendererPort(Protocol):
    async def create_from_template(
        self, template_id: TemplateId, slides: tuple[Slide, ...]
    ) -> URL: ...
