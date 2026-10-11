"""All Pydantic data models for the BugHunter platform.
Extends and replaces AutonomousQA Agent models with unified schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── BugHunter-specific Enums ──────────────────────────────────────────────────

class Severity(str, Enum):
    """Bug severity classification."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingType(str, Enum):
    """Type of bug or issue discovered."""
    CONSOLE_ERROR = "console_error"
    NETWORK_ERROR = "network_error"
    BROKEN_IMAGE = "broken_image"
    VALIDATION_ERROR = "validation_error"
    ACCESSIBILITY = "accessibility"
    FUNCTIONAL_BUG = "functional_bug"
    VISUAL_REGRESSION = "visual_regression"
    PERFORMANCE = "performance"


class ScanStatus(str, Enum):
    """Status of a scan run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── BugHunter Core Models ─────────────────────────────────────────────────────


class BugFinding(BaseModel):
    """A single bug or issue discovered during exploration."""
    id: str = ""
    scan_id: str = ""
    finding_type: FindingType = FindingType.FUNCTIONAL_BUG
    severity: Severity = Severity.MEDIUM
    title: str
    description: str = ""
    url: str = ""
    selector: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    screenshot_path: Path | None = None
    reproduction_steps: list[str] = Field(default_factory=list)
    recommended_fix: str = ""
    ai_analysis: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExplorationState(BaseModel):
    """Mutable state of the exploration agent."""
    base_url: str
    visited_urls: set[str] = Field(default_factory=set)
    action_history: list[dict[str, Any]] = Field(default_factory=list)
    steps: int = 0
    todo_queue: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ScanConfig(BaseModel):
    """Configuration for a BugHunter scan request."""
    url: str
    max_depth: int = 3
    browser: str = "chromium"
    headless: bool = True
    enable_a11y: bool = True
    enable_visual_diff: bool = False
    enable_exploration: bool = True
    max_actions: int = 50
    llm_provider: str | None = None


class ScanProgress(BaseModel):
    """Real-time progress update during a scan."""
    scan_id: str
    event_type: str
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ── CLI Bridge Result Models ─────────────────────────────────────────────────


class InstallResult(BaseModel):
    """Result of playwright install command."""

    browsers_installed: list[str]
    version: str
    stdout: str = ""
    stderr: str = ""


class CodegenResult(BaseModel):
    """Result of playwright codegen command."""

    script_path: Path
    actions_recorded: int = 0
    stdout: str = ""
    stderr: str = ""


class HARResult(BaseModel):
    """Result of playwright HAR capture."""

    har_path: Path
    request_count: int = 0
    api_request_count: int = 0
    stdout: str = ""
    stderr: str = ""


class ScreenshotResult(BaseModel):
    """Result of playwright screenshot command."""

    path: Path
    file_size_kb: float = 0.0
    stdout: str = ""
    stderr: str = ""


# ── DOM / Crawl Models ────────────────────────────────────────────────────────


class InputElement(BaseModel):
    """Represents a form input element."""

    selector: str
    input_type: str = "text"
    placeholder: str = ""
    label: str = ""
    required: bool = False
    name: str = ""


class ButtonElement(BaseModel):
    """Represents a button element."""

    selector: str
    text: str = ""
    button_type: str = "button"


class LinkElement(BaseModel):
    """Represents an anchor/link element."""

    selector: str
    href: str = ""
    text: str = ""
    is_same_origin: bool = True


class FormField(BaseModel):
    """A single field within a form."""

    selector: str
    field_type: str = "text"
    name: str = ""
    label: str = ""
    required: bool = False


class FormElement(BaseModel):
    """Represents an HTML form."""

    selector: str
    action: str = ""
    method: str = "get"
    fields: list[FormField] = Field(default_factory=list)


class SelectElement(BaseModel):
    """Represents a select dropdown."""

    selector: str
    options: list[str] = Field(default_factory=list)
    name: str = ""


class HeadingElement(BaseModel):
    """Represents a heading element (h1-h6)."""

    level: int
    text: str


class DOMSnapshot(BaseModel):
    """Full DOM snapshot of a single page."""

    url: str
    title: str = ""
    depth: int = 0
    inputs: list[InputElement] = Field(default_factory=list)
    buttons: list[ButtonElement] = Field(default_factory=list)
    links: list[LinkElement] = Field(default_factory=list)
    forms: list[FormElement] = Field(default_factory=list)
    selects: list[SelectElement] = Field(default_factory=list)
    headings: list[HeadingElement] = Field(default_factory=list)
    screenshot_path: Path | None = None
    error: str | None = None


class CrawlResult(BaseModel):
    """Aggregated result from BFS crawl."""

    base_url: str
    pages: list[DOMSnapshot] = Field(default_factory=list)
    total_pages: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ── Flow / Test Generation Models ────────────────────────────────────────────


class FlowStep(BaseModel):
    """A single step in a user flow."""

    action: str  # navigate|click|fill|select|assert|wait|hover
    selector: str = ""
    value: str | None = None
    description: str = ""
    expected_result: str = ""


class UserFlow(BaseModel):
    """An inferred user flow to be tested."""

    name: str
    priority: str = "MEDIUM"  # HIGH|MEDIUM|LOW
    description: str = ""
    preconditions: list[str] = Field(default_factory=list)
    steps: list[FlowStep] = Field(default_factory=list)
    expected_outcome: str = ""
    test_data: dict[str, Any] = Field(default_factory=dict)


class GeneratedTestSuite(BaseModel):
    """Result of AI-powered test generation."""

    file_path: Path
    test_count: int = 0
    page_objects: list[str] = Field(default_factory=list)
    syntax_valid: bool = True
    generation_errors: list[str] = Field(default_factory=list)


# ── Execution Models ──────────────────────────────────────────────────────────


class TestResult(BaseModel):
    """Result of a single test execution."""

    name: str
    status: str  # passed|failed|skipped|error
    duration: float = 0.0
    error_message: str = ""
    trace_path: Path | None = None
    page_url: str = ""


class ExecutionResult(BaseModel):
    """Aggregated test execution result."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    tests: list[TestResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    pytest_raw_path: Path | None = None


# ── Accessibility Models ──────────────────────────────────────────────────────


class A11yNode(BaseModel):
    """A DOM node with an accessibility violation."""

    selector: str = ""
    html: str = ""
    failure_summary: str = ""


class A11yViolation(BaseModel):
    """An axe-core accessibility violation."""

    rule_id: str
    impact: str  # critical|serious|moderate|minor
    description: str
    help_url: str = ""
    nodes: list[A11yNode] = Field(default_factory=list)
    page_url: str = ""


class A11yReport(BaseModel):
    """Aggregated accessibility audit report."""

    wcag_score: float = 100.0
    violations: list[A11yViolation] = Field(default_factory=list)
    pages_audited: int = 0
    total_violations: int = 0
    by_impact: dict[str, int] = Field(default_factory=dict)


# ── Visual Diff Models ────────────────────────────────────────────────────────


class VisualDiff(BaseModel):
    """Visual diff result for a single page."""

    url: str
    change_pct: float = 0.0
    diff_path: Path | None = None
    before_path: Path | None = None
    after_path: Path | None = None
    changed_pixels: int = 0
    total_pixels: int = 0


class VisualDiffResult(BaseModel):
    """Aggregated visual diff results."""

    diffs: list[VisualDiff] = Field(default_factory=list)
    total_pages: int = 0
    pages_changed: int = 0


# ── Severity Scoring Models ───────────────────────────────────────────────────


class ScoredFailure(BaseModel):
    """A test failure with AI-assigned severity."""

    test_name: str
    severity: str  # CRITICAL|HIGH|MEDIUM|LOW
    reason: str = ""
    is_likely_flaky: bool = False
    reproduction_steps: list[str] = Field(default_factory=list)
    recommended_fix: str = ""
    original_error: str = ""


# ── Agent Config ──────────────────────────────────────────────────────────────


class AgentConfig(BaseModel):
    """Full configuration for an agent run."""

    url: str
    max_depth: int = 3
    browsers: list[str] = Field(default_factory=lambda: ["chromium"])
    browser: str = "chromium"  # Primary browser for exploration
    headless: bool = True
    a11y: bool = True
    visual_diff: bool = False
    interactive: bool = False
    run_id: str = ""
    reports_dir: Path = Path("reports")
    model: str = "gpt-4o-mini"
    log_level: str = "INFO"
    max_actions: int = 50  # Maximum exploration actions


# ── Aggregated Run Data ───────────────────────────────────────────────────────


class RunData(BaseModel):
    """Complete data from a single agent run — passed to reporters."""

    run_id: str
    config: AgentConfig
    started_at: datetime
    finished_at: datetime | None = None
    playwright_version: str = ""

    # Step outputs
    crawl_result: CrawlResult | None = None
    codegen_result: CodegenResult | None = None
    har_result: HARResult | None = None
    flows: list[UserFlow] = Field(default_factory=list)
    test_suite: GeneratedTestSuite | None = None
    execution_result: ExecutionResult | None = None
    a11y_report: A11yReport | None = None
    visual_diff_result: VisualDiffResult | None = None
    scored_failures: list[ScoredFailure] = Field(default_factory=list)

    # Derived summary
    severity_breakdown: dict[str, int] = Field(
        default_factory=lambda: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    )
    run_dir: Path = Path("reports")

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if not self.execution_result or self.execution_result.total == 0:
            return 0.0
        return (self.execution_result.passed / self.execution_result.total) * 100

    @property
    def duration_seconds(self) -> float:
        """Total run duration in seconds."""
        if not self.finished_at:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()
