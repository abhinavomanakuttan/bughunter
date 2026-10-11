"""
BugHunter — Scan Orchestrator
Coordinates the full scan workflow:
1. BFS Crawl → DOM snapshots
2. Explore (Observe-Plan-Act-Verify) → Bug findings
3. Accessibility audit (axe-core)
4. Flow inference + Test generation → pytest files
5. Test execution → pass/fail results
6. Severity scoring (AI)
7. Report generation (HTML, JSON, Markdown)
"""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator

from backend.agent.crawler import SiteCrawler
from backend.agent.executor import TestExecutor
from backend.agent.explorer import ExplorationAgent
from backend.agent.flow_inferencer import FlowInferencer
from backend.agent.test_generator import TestGenerator
from backend.analysis.accessibility import AccessibilityAuditor
from backend.analysis.severity_scorer import SeverityScorer
from backend.cli_bridge import PlaywrightCLI
from backend.config import get_settings
from backend.db.database import BugHunterDB
from backend.models import AgentConfig, BugFinding, RunData, ScanConfig, ScanStatus
from backend.reporting.html_reporter import HTMLReporter
from backend.reporting.json_reporter import JSONReporter
from backend.services.llm import LLMService, get_llm_service
from backend.services.url_validator import URLValidationError, validate_scan_url

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """
    Orchestrates the complete BugHunter scan workflow.
    Emits Server-Sent Events via an async queue for real-time frontend updates.
    """

    def __init__(self, db: BugHunterDB) -> None:
        self._db = db
        self._active_scans: dict[str, asyncio.Queue] = {}
        self._main_loops: dict[str, asyncio.AbstractEventLoop] = {}

    def _make_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Format a Server-Sent Event string."""
        import json
        payload = json.dumps({"type": event_type, **data})
        return f"data: {payload}\n\n"

    def get_event_queue(self, scan_id: str) -> asyncio.Queue | None:
        """Get the SSE event queue for an active scan."""
        return self._active_scans.get(scan_id)

    async def start_scan(self, config: ScanConfig) -> str:
        """
        Start a new scan asynchronously.

        Args:
            config: Scan configuration

        Returns:
            scan_id for tracking
        """
        settings = get_settings()

        # Validate URL
        try:
            validated_url = validate_scan_url(config.url, demo_mode=settings.demo_mode)
        except URLValidationError as exc:
            raise ValueError(f"URL validation failed: {exc}") from exc

        scan_id = f"scan_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Create event queue for SSE streaming
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._active_scans[scan_id] = queue

        # Record main loop for thread-safe event posting
        main_loop = asyncio.get_running_loop()
        self._main_loops[scan_id] = main_loop

        # Create DB record
        await self._db.create_scan(
            scan_id=scan_id,
            url=validated_url,
            config=config.model_dump(),
        )

        # Run scan in dedicated worker thread with Proactor loop on Windows
        def _worker() -> None:
            if sys.platform == "win32":
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._run_scan(scan_id, validated_url, config, queue)
                )
            finally:
                loop.close()

        thread = threading.Thread(target=_worker, name=f"scan-{scan_id}", daemon=True)
        thread.start()

        return scan_id

    async def _emit(self, queue: asyncio.Queue, event_type: str, data: dict[str, Any]) -> None:
        """Put an event on the SSE queue thread-safely."""
        event = {"type": event_type, **data}
        scan_id = data.get("scan_id", "")
        main_loop = self._main_loops.get(scan_id)
        if not main_loop and self._main_loops:
            main_loop = next(iter(self._main_loops.values()), None)

        if main_loop and main_loop.is_running():
            try:
                main_loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception:
                pass
        else:
            try:
                queue.put_nowait(event)
            except Exception:
                pass

    async def _run_scan(
        self,
        scan_id: str,
        url: str,
        config: ScanConfig,
        queue: asyncio.Queue,
    ) -> None:
        """Full scan pipeline — runs in background."""
        settings = get_settings()
        run_dir = Path(settings.reports_dir) / scan_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Select LLM provider
        llm_provider = config.llm_provider or settings.llm_provider
        llm_service = LLMService(provider=llm_provider)

        try:
            llm_client = llm_service.get_openai_client()
            llm_model = llm_service.get_model_name()
        except Exception as exc:
            logger.warning("LLM not available (%s) — AI features disabled", exc)
            llm_client = None
            llm_model = ""

        await self._emit(queue, "started", {"scan_id": scan_id, "url": url})

        bug_findings: list[BugFinding] = []
        pages_crawled = 0
        crawl_result = None
        execution_result = None
        a11y_report = None
        test_suite = None
        scored_failures = []

        try:
            # ── Phase 1: BFS Crawl ────────────────────────────────────────────
            await self._emit(queue, "phase", {"phase": "crawl", "message": "Starting BFS crawl..."})
            cli = PlaywrightCLI()
            crawler = SiteCrawler(cli=cli)

            try:
                crawl_result = await asyncio.wait_for(
                    crawler.crawl(
                        url=url,
                        max_depth=config.max_depth,
                        browser_type=config.browser,
                        run_dir=run_dir,
                        headless=config.headless,
                    ),
                    timeout=settings.scan_timeout_seconds,
                )
                pages_crawled = crawl_result.total_pages
                await self._emit(queue, "crawl_complete", {
                    "pages": pages_crawled,
                    "errors": len(crawl_result.errors),
                })
            except asyncio.TimeoutError:
                logger.error("BFS crawl timed out")
                await self._emit(queue, "error", {"message": "Crawl timed out"})

            # ── Phase 2: Exploration (Observe-Plan-Act-Verify) ────────────────
            if config.enable_exploration:
                await self._emit(queue, "phase", {"phase": "explore", "message": "Exploring with AI agent..."})

                agent_config = AgentConfig(
                    url=url,
                    max_depth=config.max_depth,
                    browsers=[config.browser],
                    browser=config.browser,
                    headless=config.headless,
                    run_id=scan_id,
                    reports_dir=Path(settings.reports_dir),
                    model=llm_model,
                    max_actions=config.max_actions,
                )

                def progress_cb(event: dict) -> None:
                    main_loop = self._main_loops.get(scan_id)
                    if main_loop and main_loop.is_running():
                        main_loop.call_soon_threadsafe(queue.put_nowait, event)
                    else:
                        try:
                            queue.put_nowait(event)
                        except Exception:
                            pass

                explorer = ExplorationAgent(
                    config=agent_config,
                    llm_client=llm_client,
                    llm_model=llm_model,
                    progress_callback=progress_cb,
                )

                try:
                    exploration_findings = await asyncio.wait_for(
                        explorer.explore(run_dir=run_dir),
                        timeout=settings.scan_timeout_seconds,
                    )
                    bug_findings.extend(exploration_findings)
                except asyncio.TimeoutError:
                    logger.error("Exploration timed out")
                    await self._emit(queue, "error", {"message": "Exploration timed out"})

                await self._emit(queue, "explore_complete", {
                    "findings": len(bug_findings),
                })

            # ── Phase 3: Accessibility Audit ──────────────────────────────────
            if config.enable_a11y and crawl_result:
                await self._emit(queue, "phase", {"phase": "a11y", "message": "Running accessibility audit..."})
                try:
                    auditor = AccessibilityAuditor()
                    a11y_report = await asyncio.wait_for(
                        auditor.audit(crawl_result.pages, browser_type=config.browser),
                        timeout=120,
                    )
                    # Convert a11y violations to findings
                    for violation in (a11y_report.violations or [])[:50]:
                        from backend.models import FindingType, Severity
                        severity_map = {
                            "critical": Severity.CRITICAL,
                            "serious": Severity.HIGH,
                            "moderate": Severity.MEDIUM,
                            "minor": Severity.LOW,
                        }
                        finding = BugFinding(
                            id=str(uuid.uuid4()),
                            scan_id=scan_id,
                            finding_type=FindingType.ACCESSIBILITY,
                            severity=severity_map.get(violation.impact, Severity.MEDIUM),
                            title=f"Accessibility: {violation.rule_id} — {violation.description[:80]}",
                            description=violation.description,
                            url=violation.page_url,
                            evidence={"rule_id": violation.rule_id, "help_url": violation.help_url},
                        )
                        bug_findings.append(finding)

                    await self._emit(queue, "a11y_complete", {
                        "wcag_score": a11y_report.wcag_score,
                        "violations": a11y_report.total_violations,
                    })
                except Exception as exc:
                    logger.warning("Accessibility audit failed: %s", exc)
                    await self._emit(queue, "error", {"message": f"A11y audit failed: {exc}"})

            # ── Phase 4: AI Flow Inference + Test Generation ──────────────────
            flows = []
            if llm_client and crawl_result:
                await self._emit(queue, "phase", {"phase": "test_gen", "message": "Inferring user flows & generating tests..."})
                try:
                    inferencer = FlowInferencer(client=llm_client, model=llm_model)
                    flows = await asyncio.wait_for(
                        inferencer.infer(crawl_result),
                        timeout=120,
                    )
                    await self._emit(queue, "flows_inferred", {"count": len(flows)})

                    if flows:
                        generator = TestGenerator(client=llm_client, model=llm_model)
                        test_suite = await asyncio.wait_for(
                            generator.generate(flows, base_url=url, run_dir=run_dir),
                            timeout=120,
                        )
                        await self._emit(queue, "tests_generated", {
                            "count": test_suite.test_count,
                            "syntax_valid": test_suite.syntax_valid,
                        })
                except Exception as exc:
                    logger.warning("Test generation failed: %s", exc)
                    await self._emit(queue, "error", {"message": f"Test generation failed: {exc}"})

            # ── Phase 5: Test Execution ───────────────────────────────────────
            if test_suite and test_suite.syntax_valid:
                await self._emit(queue, "phase", {"phase": "test_run", "message": "Running generated tests..."})
                try:
                    agent_config = AgentConfig(
                        url=url,
                        browsers=[config.browser],
                        headless=config.headless,
                        run_id=scan_id,
                        reports_dir=Path(settings.reports_dir),
                    )
                    executor = TestExecutor(cli=cli)
                    execution_result = await asyncio.wait_for(
                        executor.run(suite=test_suite, config=agent_config, run_dir=run_dir),
                        timeout=300,
                    )
                    await self._emit(queue, "tests_run", {
                        "total": execution_result.total,
                        "passed": execution_result.passed,
                        "failed": execution_result.failed,
                    })
                except Exception as exc:
                    logger.warning("Test execution failed: %s", exc)
                    await self._emit(queue, "error", {"message": f"Test execution failed: {exc}"})

            # ── Phase 6: Severity Scoring ─────────────────────────────────────
            if llm_client and execution_result and execution_result.failed > 0:
                await self._emit(queue, "phase", {"phase": "scoring", "message": "Scoring failure severity..."})
                try:
                    scorer = SeverityScorer(client=llm_client, model=llm_model)
                    scored_failures = await asyncio.wait_for(
                        scorer.score(execution_result, target_url=url),
                        timeout=60,
                    )
                    await self._emit(queue, "scoring_complete", {"scored": len(scored_failures)})
                except Exception as exc:
                    logger.warning("Severity scoring failed: %s", exc)

            # ── Phase 7: Save findings to DB ──────────────────────────────────
            for finding in bug_findings:
                try:
                    await self._db.add_finding(
                        finding_id=finding.id or str(uuid.uuid4()),
                        scan_id=scan_id,
                        finding_type=finding.finding_type.value,
                        severity=finding.severity.value,
                        title=finding.title,
                        description=finding.description,
                        url=finding.url,
                        selector=finding.selector,
                        evidence=finding.evidence,
                        screenshot_path=str(finding.screenshot_path) if finding.screenshot_path else None,
                        reproduction_steps=finding.reproduction_steps,
                        recommended_fix=finding.recommended_fix,
                    )
                except Exception as exc:
                    logger.warning("Failed to save finding: %s", exc)

            # ── Phase 8: Report Generation ────────────────────────────────────
            await self._emit(queue, "phase", {"phase": "report", "message": "Generating reports..."})

            html_report_path = None
            json_report_path = None

            if crawl_result:
                try:
                    from backend.models import (
                        ExecutionResult,
                        RunData,
                        ScoredFailure,
                    )

                    run_data = RunData(
                        run_id=scan_id,
                        config=AgentConfig(
                            url=url,
                            browsers=[config.browser],
                            headless=config.headless,
                            run_id=scan_id,
                            reports_dir=Path(settings.reports_dir),
                        ),
                        started_at=datetime.now(UTC),
                        finished_at=datetime.now(UTC),
                        crawl_result=crawl_result,
                        flows=flows,
                        test_suite=test_suite,
                        execution_result=execution_result,
                        a11y_report=a11y_report,
                        scored_failures=[
                            sf for sf in scored_failures
                        ],
                        run_dir=run_dir,
                    )

                    html_reporter = HTMLReporter()
                    html_report_path = str(html_reporter.generate(run_data))

                    json_reporter = JSONReporter()
                    json_report_path = str(json_reporter.generate(run_data))

                except Exception as exc:
                    logger.warning("Report generation failed: %s", exc)

            # ── Mark scan complete ────────────────────────────────────────────
            await self._db.finish_scan(
                scan_id=scan_id,
                status=ScanStatus.COMPLETED.value,
                pages_crawled=pages_crawled,
                findings_count=len(bug_findings),
                tests_total=execution_result.total if execution_result else 0,
                tests_passed=execution_result.passed if execution_result else 0,
                tests_failed=execution_result.failed if execution_result else 0,
                wcag_score=a11y_report.wcag_score if a11y_report else 100.0,
                report_html_path=html_report_path,
                report_json_path=json_report_path,
            )

            await self._emit(queue, "completed", {
                "scan_id": scan_id,
                "findings": len(bug_findings),
                "pages": pages_crawled,
                "report_html": html_report_path,
                "report_json": json_report_path,
            })

        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
            logger.exception("Scan %s failed: %s", scan_id, err_msg)
            await self._db.finish_scan(
                scan_id=scan_id,
                status=ScanStatus.FAILED.value,
                error_message=err_msg,
            )
            await self._emit(queue, "failed", {"scan_id": scan_id, "error": err_msg})

        finally:
            # Clean up queue after delay
            await asyncio.sleep(30)
            self._active_scans.pop(scan_id, None)
