"""Domain service for lightweight tone calibration heuristics."""

from __future__ import annotations

import re

from searce_scout.messaging.domain.value_objects.tone import Tone


class ToneCalibrationService:
    """Applies rule-based tone adjustments to message body text.

    Heavy rewriting is delegated to the AI message generator port;
    this service handles only lightweight, deterministic heuristic
    transformations.
    """

    # Patterns considered too informal for the professional tone
    _SLANG_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(gonna|wanna|gotta|kinda|sorta)\b", re.IGNORECASE),
        re.compile(r"\b(lol|lmao|rofl|omg|btw|tbh|imo|imho)\b", re.IGNORECASE),
    )

    # Emoji unicode range (common emoji blocks)
    _EMOJI_PATTERN: re.Pattern[str] = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map
        "\U0001f1e0-\U0001f1ff"  # flags
        "\U00002702-\U000027b0"  # dingbats
        "\U0000fe00-\U0000fe0f"  # variation selectors
        "\U0000200d"  # zero width joiner
        "]+",
        re.UNICODE,
    )

    # Replacement mapping for slang -> professional equivalents
    _SLANG_REPLACEMENTS: dict[str, str] = {
        "gonna": "going to",
        "wanna": "want to",
        "gotta": "have to",
        "kinda": "somewhat",
        "sorta": "somewhat",
    }

    # Markers that signal a lighter, witty tone
    _WITTY_OPENERS: tuple[str, ...] = (
        "Here's the thing -- ",
        "Real talk: ",
        "Plot twist: ",
    )

    def calibrate(self, body: str, target_tone: Tone) -> str:
        """Apply heuristic tone adjustments to a message body.

        Args:
            body: The original message body text.
            target_tone: The desired tone for the output.

        Returns:
            The adjusted body text. For PROFESSIONAL_CONSULTANT, slang
            and emojis are removed. For WITTY_TECH_PARTNER, lighter
            phrasing markers are prepended if not already present.
        """
        if target_tone is Tone.PROFESSIONAL_CONSULTANT:
            return self._make_professional(body)
        elif target_tone is Tone.WITTY_TECH_PARTNER:
            return self._make_witty(body)
        return body

    def _make_professional(self, body: str) -> str:
        """Remove slang, abbreviations, and emojis for a professional tone."""
        result = body

        # Replace known slang with professional equivalents
        for slang, replacement in self._SLANG_REPLACEMENTS.items():
            pattern = re.compile(rf"\b{slang}\b", re.IGNORECASE)
            result = pattern.sub(replacement, result)

        # Remove remaining informal abbreviations
        for pattern in self._SLANG_PATTERNS:
            result = pattern.sub("", result)

        # Remove emojis
        result = self._EMOJI_PATTERN.sub("", result)

        # Clean up extra whitespace introduced by removals
        result = re.sub(r"  +", " ", result).strip()

        return result

    def _make_witty(self, body: str) -> str:
        """Add lighter phrasing markers for a witty tech partner tone."""
        # If the body already starts with one of our witty openers, leave it
        for opener in self._WITTY_OPENERS:
            if body.startswith(opener):
                return body

        # Prepend the first witty opener as a lightweight marker
        # Full rewriting is handled by the AI generator port
        return f"{self._WITTY_OPENERS[0]}{body}"
