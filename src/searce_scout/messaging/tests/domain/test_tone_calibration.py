"""Pure domain tests for ToneCalibrationService.

No mocks — exercises the heuristic tone transformations for
PROFESSIONAL_CONSULTANT and WITTY_TECH_PARTNER.
"""

from searce_scout.messaging.domain.services.tone_calibration import (
    ToneCalibrationService,
)
from searce_scout.messaging.domain.value_objects.tone import Tone


class TestCalibrateProfessional:
    def test_calibrate_professional_removes_slang(self) -> None:
        service = ToneCalibrationService()
        body = "We're gonna help you scale. Wanna chat? lol"
        result = service.calibrate(body, Tone.PROFESSIONAL_CONSULTANT)

        assert "gonna" not in result
        assert "going to" in result
        assert "wanna" not in result.lower()
        assert "want to" in result.lower() or "Want to" in result
        assert "lol" not in result.lower()

    def test_calibrate_professional_removes_emojis(self) -> None:
        service = ToneCalibrationService()
        body = "Great news! \U0001f680 Let's talk."
        result = service.calibrate(body, Tone.PROFESSIONAL_CONSULTANT)
        assert "\U0001f680" not in result

    def test_calibrate_professional_cleans_extra_whitespace(self) -> None:
        service = ToneCalibrationService()
        body = "Hey btw we should chat"
        result = service.calibrate(body, Tone.PROFESSIONAL_CONSULTANT)
        assert "  " not in result


class TestCalibrateWitty:
    def test_calibrate_witty_adds_lighter_tone(self) -> None:
        service = ToneCalibrationService()
        body = "We help companies migrate to the cloud."
        result = service.calibrate(body, Tone.WITTY_TECH_PARTNER)

        assert result.startswith("Here's the thing -- ")
        assert "We help companies migrate to the cloud." in result

    def test_calibrate_witty_does_not_double_prepend(self) -> None:
        service = ToneCalibrationService()
        body = "Here's the thing -- already witty."
        result = service.calibrate(body, Tone.WITTY_TECH_PARTNER)

        # Should not double-prepend
        assert result == body
