"""
BugHunter — Bug Detector: Console Errors
Ported from qa-agent/src/tools/console-errors.ts (crislerwin/qa-agent)

Monitors browser console for JavaScript errors and warnings using Playwright event listeners.
"""
from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import ConsoleMessage, Page

logger = logging.getLogger(__name__)

# Console message types that indicate bugs
_ERROR_TYPES = {"error", "warning"}

# Filter out known noise (e.g. browser extension messages, analytics)
_IGNORED_PATTERNS = [
    "favicon.ico",
    "favicon.png",
    "__webpack_dev_server__",
    "[HMR]",
    "[WDS]",
    "hot-update",
    "DevTools",
    "Extension",
    "content_script",
    "net::ERR_ABORTED",  # Usually caused by navigation, not bugs
]


class ConsoleMonitor:
    """
    Attaches to a Playwright page and records console errors/warnings.
    Call attach() before navigation, call get_errors() to retrieve captured messages.
    """

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []

    def attach(self, page: Page) -> None:
        """
        Attach console listener to the page.
        Must be called before navigating to the target URL.
        """
        page.on("console", self._handle_console)
        logger.debug("Console monitor attached to page")

    def _handle_console(self, msg: ConsoleMessage) -> None:
        """Handle incoming console message."""
        msg_type = msg.type
        if msg_type not in _ERROR_TYPES:
            return

        text = msg.text
        # Filter noise
        for pattern in _IGNORED_PATTERNS:
            if pattern.lower() in text.lower():
                return

        entry = {
            "type": msg_type,
            "text": text[:2000],
            "url": "",  # Playwright doesn't always provide source URL
            "line": None,
            "col": None,
        }

        # Try to get location
        try:
            location = msg.location
            if location:
                entry["url"] = location.get("url", "")
                entry["line"] = location.get("lineNumber")
                entry["col"] = location.get("columnNumber")
        except Exception:
            pass

        self._messages.append(entry)

        if msg_type == "error":
            logger.info("Console error: %s", text[:200])

    def get_errors(self) -> list[dict[str, Any]]:
        """Return all captured console errors/warnings."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear recorded messages."""
        self._messages.clear()
