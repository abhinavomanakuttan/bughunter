"""
BugHunter — Exploration Agent implementing Observe-Plan-Act-Verify loop.

Architecture inspired by crislerwin/qa-agent's ExploratoryAgent TypeScript class.
Implemented in Python using Playwright async API + configurable LLM.

The agent:
1. Observes: captures DOM snapshot, console errors, network failures, broken images
2. Plans: sends observation to LLM for next action decision
3. Acts: executes the chosen browser action
4. Verifies: runs all detectors again after each action
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, Page, async_playwright

from backend.detectors.broken_images import find_broken_images
from backend.detectors.console_errors import ConsoleMonitor
from backend.detectors.network_errors import NetworkMonitor
from backend.detectors.validation_errors import find_validation_errors
from backend.models import (
    AgentConfig,
    BugFinding,
    ExplorationState,
    FindingType,
    Severity,
)

logger = logging.getLogger(__name__)

_OBSERVE_JS = """
() => {
    const safeText = (el) => (el ? el.textContent.trim().substring(0, 150) : '');
    const safeAttr = (el, attr) => (el ? (el.getAttribute(attr) || '') : '');

    const clickable = Array.from(document.querySelectorAll(
        'button:not([disabled]), a[href], input[type="submit"], input[type="button"], [role="button"], [onclick]'
    )).slice(0, 20).map(el => ({
        selector: el.id ? '#' + el.id : (el.tagName.toLowerCase() === 'a' ? 'a[href="' + el.getAttribute('href') + '"]' : el.tagName.toLowerCase()),
        text: safeText(el) || el.value || el.getAttribute('aria-label') || '',
        tag: el.tagName.toLowerCase(),
        href: el.getAttribute('href') || '',
        type: el.getAttribute('type') || '',
    }));

    const forms = Array.from(document.querySelectorAll('form')).slice(0, 5).map(form => ({
        selector: form.id ? '#' + form.id : 'form',
        action: form.action || '',
        method: form.method || 'get',
        field_count: form.querySelectorAll('input, select, textarea').length,
    }));

    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select')).slice(0, 10).map(el => ({
        selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : el.tagName.toLowerCase()),
        type: el.type || el.tagName.toLowerCase(),
        placeholder: el.placeholder || '',
        label: '',
        required: el.required || false,
    }));

    const headings = Array.from(document.querySelectorAll('h1,h2,h3')).slice(0, 5).map(el => el.textContent.trim());

    return {
        title: document.title,
        url: window.location.href,
        clickable: clickable,
        forms: forms,
        inputs: inputs,
        headings: headings,
        body_text_preview: document.body ? document.body.innerText.substring(0, 500) : '',
    };
}
"""

_PLAN_SYSTEM_PROMPT = """You are an expert QA engineer autonomously exploring a web application to find bugs.

You receive a JSON observation of the current page state plus history of actions taken.
Decide the SINGLE best next action to explore and find bugs.

Focus on:
- Clicking buttons and links to discover new functionality
- Filling and submitting forms (use realistic test data)
- Testing edge cases: empty inputs, invalid data, special characters
- Navigating to unvisited pages

Return ONLY valid JSON with this exact schema:
{
  "action": "navigate|click|fill|submit|scan|done",
  "selector": "CSS selector or URL (for navigate)",
  "value": "text to fill (for fill action)",
  "reason": "brief explanation of why this action"
}

Action types:
- "navigate": go to a URL (set selector = the URL)
- "click": click a button/link (set selector = CSS selector)
- "fill": type text into an input (set selector = input selector, value = text)
- "submit": submit a form (set selector = form/button selector)
- "scan": run all bug detectors on current page (no selector needed)
- "done": stop exploration (use when all interesting pages explored)
"""


class ExplorationAgent:
    """
    Autonomous exploration agent implementing Observe-Plan-Act-Verify loop.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: Any = None,
        llm_model: str = "gpt-4o-mini",
        progress_callback: Any = None,
    ) -> None:
        self._config = config
        self._llm = llm_client
        self._llm_model = llm_model
        self._progress_cb = progress_callback
        self._state = ExplorationState(base_url=config.url)
        self._findings: list[BugFinding] = []
        self._screenshots: list[Path] = []

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit a progress event to the callback if registered."""
        if self._progress_cb:
            try:
                self._progress_cb({"type": event_type, **data})
            except Exception:
                pass

    async def _plan_action(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Send observation to LLM and get next action."""
        if not self._llm:
            # Fallback: use a simple heuristic if no LLM
            return {"action": "scan", "selector": "", "value": "", "reason": "No LLM configured — running scan"}

        history_summary = self._state.action_history[-5:]  # last 5 actions
        user_content = (
            f"Current URL: {observation.get('url', 'unknown')}\n"
            f"Page Title: {observation.get('title', '')}\n"
            f"Headings: {', '.join(observation.get('headings', []))}\n\n"
            f"DOM Observation:\n```json\n{json.dumps(observation, indent=2)[:3000]}\n```\n\n"
            f"Action History (last 5):\n{json.dumps(history_summary, indent=2)}\n\n"
            f"Visited URLs: {list(self._state.visited_urls)[:10]}\n\n"
            "What should be the next action? Return ONLY JSON."
        )

        try:
            response = await self._llm.chat.completions.create(
                model=self._llm_model,
                temperature=0,
                messages=[
                    {"role": "system", "content": _PLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            raw = response.choices[0].message.content or "{}"
            # Strip markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:])
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LLM planning failed: %s", exc)
            return {"action": "scan", "selector": "", "value": "", "reason": f"LLM error: {exc}"}

    def _is_same_origin(self, url: str) -> bool:
        """Check if URL is same origin as base."""
        try:
            base = urlparse(self._config.url)
            target = urlparse(url)
            return base.netloc == target.netloc
        except Exception:
            return False

    async def _run_detectors(self, page: Page, console_mon: ConsoleMonitor, network_mon: NetworkMonitor) -> list[BugFinding]:
        """Run all detectors on current page and return new findings."""
        new_findings: list[BugFinding] = []
        url = page.url

        # Broken images
        broken_imgs = await find_broken_images(page)
        for img in broken_imgs:
            finding = BugFinding(
                id=str(uuid.uuid4()),
                scan_id=self._config.run_id,
                finding_type=FindingType.BROKEN_IMAGE,
                severity=Severity.MEDIUM,
                title=f"Broken image: {img.get('src', 'unknown src')[:80]}",
                description=img.get("reason", ""),
                url=url,
                selector=img.get("selector", ""),
                evidence=img,
            )
            new_findings.append(finding)

        # Console errors
        for err in console_mon.get_errors():
            severity = Severity.HIGH if err.get("type") == "error" else Severity.LOW
            finding = BugFinding(
                id=str(uuid.uuid4()),
                scan_id=self._config.run_id,
                finding_type=FindingType.CONSOLE_ERROR,
                severity=severity,
                title=f"Console {err.get('type', 'error')}: {err.get('text', '')[:80]}",
                description=err.get("text", ""),
                url=url,
                evidence=err,
            )
            new_findings.append(finding)
        console_mon.clear()

        # Network errors
        for net in network_mon.get_failures():
            severity = Severity.HIGH if net.get("status", 0) >= 500 else Severity.MEDIUM
            finding = BugFinding(
                id=str(uuid.uuid4()),
                scan_id=self._config.run_id,
                finding_type=FindingType.NETWORK_ERROR,
                severity=severity,
                title=f"Network {net.get('error', 'failure')}: {net.get('url', '')[:80]}",
                description=net.get("error", ""),
                url=url,
                evidence=net,
            )
            new_findings.append(finding)
        network_mon.clear()

        # Validation errors
        validation_errors = await find_validation_errors(page)
        for ve in validation_errors:
            finding = BugFinding(
                id=str(uuid.uuid4()),
                scan_id=self._config.run_id,
                finding_type=FindingType.VALIDATION_ERROR,
                severity=Severity.MEDIUM,
                title=f"Validation error: {ve.get('text', '')[:80]}",
                description=ve.get("text", ""),
                url=url,
                selector=ve.get("selector", ""),
                evidence=ve,
            )
            new_findings.append(finding)

        return new_findings

    async def _take_screenshot(self, page: Page, run_dir: Path, label: str) -> Path | None:
        """Take a screenshot and return the path."""
        try:
            slug = re.sub(r"[^\w]", "_", urlparse(page.url).path or "home")[:30]
            path = run_dir / "screenshots" / f"{label}_{slug}_{int(time.time())}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(path), full_page=True)
            return path
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            return None

    async def explore(self, run_dir: Path) -> list[BugFinding]:
        """
        Main exploration loop. Returns all detected findings.

        Args:
            run_dir: Directory to save screenshots and evidence

        Returns:
            List of BugFinding objects discovered during exploration
        """
        run_dir.mkdir(parents=True, exist_ok=True)
        all_findings: list[BugFinding] = []
        max_actions = self._config.max_actions
        action_count = 0

        self._emit("status", {"message": f"Starting exploration: {self._config.url}"})

        async with async_playwright() as pw:
            browser_launcher = getattr(pw, self._config.browser, pw.chromium)
            browser: Browser = await browser_launcher.launch(headless=self._config.headless)

            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    ignore_https_errors=True,
                )
                page = await context.new_page()

                # Attach detectors
                console_mon = ConsoleMonitor()
                network_mon = NetworkMonitor()
                console_mon.attach(page)
                network_mon.attach(page)

                # Initial navigation
                await page.goto(self._config.url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(0.5)
                self._state.visited_urls.add(self._config.url)

                # Initial screenshot
                await self._take_screenshot(page, run_dir, "initial")

                # Exploration loop
                while action_count < max_actions:
                    # OBSERVE
                    try:
                        observation = await page.evaluate(_OBSERVE_JS)
                    except Exception as exc:
                        logger.warning("Observation failed: %s", exc)
                        break

                    current_url = page.url

                    self._emit("observe", {
                        "url": current_url,
                        "title": observation.get("title", ""),
                        "step": action_count,
                    })

                    # PLAN
                    action_plan = await self._plan_action(observation)
                    action = action_plan.get("action", "scan")
                    selector = action_plan.get("selector", "")
                    value = action_plan.get("value", "")
                    reason = action_plan.get("reason", "")

                    logger.info("Step %d: action=%s selector=%s reason=%s",
                                action_count, action, selector[:50], reason[:80])
                    self._emit("plan", {"action": action, "selector": selector, "reason": reason, "step": action_count})

                    # Check termination
                    if action == "done":
                        logger.info("Agent decided exploration is complete")
                        break

                    # ACT
                    try:
                        if action == "navigate":
                            nav_url = selector
                            if not nav_url.startswith("http"):
                                nav_url = urljoin(self._config.url, selector)
                            if self._is_same_origin(nav_url) and nav_url not in self._state.visited_urls:
                                await page.goto(nav_url, wait_until="domcontentloaded", timeout=20000)
                                await asyncio.sleep(0.5)
                                self._state.visited_urls.add(nav_url)

                        elif action == "click":
                            if selector:
                                await page.locator(selector).first.click(timeout=10000)
                                await asyncio.sleep(0.5)

                        elif action == "fill":
                            if selector and value:
                                await page.locator(selector).first.fill(value, timeout=10000)

                        elif action == "submit":
                            if selector:
                                await page.locator(selector).first.click(timeout=10000)
                                await asyncio.sleep(1)

                    except Exception as exc:
                        logger.warning("Action execution failed [%s %s]: %s", action, selector[:50], exc)
                        # Add an action failure finding
                        finding = BugFinding(
                            id=str(uuid.uuid4()),
                            scan_id=self._config.run_id,
                            finding_type=FindingType.FUNCTIONAL_BUG,
                            severity=Severity.MEDIUM,
                            title=f"Action failed: {action} on {selector[:50]}",
                            description=str(exc),
                            url=current_url,
                            selector=selector,
                        )
                        all_findings.append(finding)

                    # Record action history
                    self._state.action_history.append({
                        "step": action_count,
                        "action": action,
                        "selector": selector,
                        "url": current_url,
                    })

                    # VERIFY — run detectors
                    new_findings = await self._run_detectors(page, console_mon, network_mon)
                    if new_findings:
                        all_findings.extend(new_findings)
                        self._emit("findings", {
                            "count": len(new_findings),
                            "total": len(all_findings),
                            "step": action_count,
                        })
                        # Screenshot on finding
                        screenshot_path = await self._take_screenshot(page, run_dir, f"finding_{action_count}")
                        if screenshot_path:
                            for f in new_findings:
                                f.screenshot_path = screenshot_path

                    action_count += 1

                # Final scan
                logger.info("Running final detector scan...")
                final_findings = await self._run_detectors(page, console_mon, network_mon)
                all_findings.extend(final_findings)

                # Final screenshot
                await self._take_screenshot(page, run_dir, "final")

                await context.close()
            finally:
                await browser.close()

        # Deduplicate findings by title
        seen_titles: set[str] = set()
        unique_findings: list[BugFinding] = []
        for f in all_findings:
            if f.title not in seen_titles:
                seen_titles.add(f.title)
                unique_findings.append(f)

        logger.info(
            "Exploration complete: %d actions, %d unique findings",
            action_count,
            len(unique_findings),
        )
        self._emit("complete", {
            "actions": action_count,
            "findings": len(unique_findings),
            "visited_urls": len(self._state.visited_urls),
        })

        return unique_findings
