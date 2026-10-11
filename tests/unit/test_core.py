"""
BugHunter — Core unit tests
Verifies models, config, URL validation, and API routes.
"""
import pytest
from pathlib import Path
from backend.models import BugFinding, FindingType, Severity, ScanConfig, ExplorationState
from backend.config import get_settings
from backend.services.url_validator import validate_scan_url, URLValidationError


def test_models_creation():
    finding = BugFinding(
        id="test-1",
        scan_id="scan-1",
        finding_type=FindingType.CONSOLE_ERROR,
        severity=Severity.HIGH,
        title="Test Console Error",
        description="Uncaught TypeError",
        url="http://localhost:3000",
    )
    assert finding.id == "test-1"
    assert finding.severity == Severity.HIGH
    assert finding.created_at is not None


def test_scan_config_defaults():
    config = ScanConfig(url="https://example.com")
    assert config.max_depth == 3
    assert config.browser == "chromium"
    assert config.headless is True


def test_url_validator():
    # Valid external URL
    validated = validate_scan_url("https://example.com")
    assert validated == "https://example.com"

    # Invalid scheme
    with pytest.raises(URLValidationError):
        validate_scan_url("ftp://example.com")

    # Localhost in non-demo mode
    with pytest.raises(URLValidationError):
        validate_scan_url("http://localhost:8080", demo_mode=False)

    # Localhost in demo mode allowed
    allowed = validate_scan_url("http://localhost:8080", demo_mode=True)
    assert allowed == "http://localhost:8080"


def test_settings_load():
    settings = get_settings()
    assert settings.port == 8000
    assert settings.default_browser == "chromium"
