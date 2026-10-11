"""
BugHunter — Bug Detector: Network Errors
Ported from qa-agent/src/tools/network-errors.ts (crislerwin/qa-agent)

Monitors HTTP requests and captures 4xx/5xx failures using Playwright request event listeners.
"""
from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page, Request, Response

logger = logging.getLogger(__name__)

# Resource types to monitor (skip assets that are typically not app bugs)
_MONITORED_RESOURCE_TYPES = {
    "fetch",
    "xhr",
    "document",
    "other",
}

# Status codes indicating server/client failures
_ERROR_STATUS_CODES = set(range(400, 600))

# URLs to ignore (CDN, analytics, third-party)
_IGNORED_URL_PATTERNS = [
    "favicon.ico",
    "favicon.png",
    "google-analytics",
    "googletagmanager",
    "hotjar",
    "intercom",
    "analytics",
    "cdn.cloudflare",
    "cdnjs.cloudflare",
]


class NetworkMonitor:
    """
    Attaches to a Playwright page and records failed HTTP requests.
    Records both request failures (network level) and HTTP error responses (4xx, 5xx).
    """

    def __init__(self) -> None:
        self._failures: list[dict[str, Any]] = []
        self._pending: dict[str, Request] = {}  # url -> Request

    def attach(self, page: Page) -> None:
        """Attach network listeners to the page."""
        page.on("requestfailed", self._handle_request_failed)
        page.on("response", self._handle_response)
        logger.debug("Network monitor attached to page")

    def _should_ignore(self, url: str) -> bool:
        """Check if the URL should be ignored."""
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in _IGNORED_URL_PATTERNS)

    def _handle_request_failed(self, request: Request) -> None:
        """Handle a network-level request failure."""
        url = request.url
        if self._should_ignore(url):
            return

        failure_text = request.failure or "Unknown network failure"
        resource_type = request.resource_type

        entry = {
            "type": "network_failure",
            "url": url,
            "method": request.method,
            "resource_type": resource_type,
            "status": None,
            "error": failure_text,
        }
        self._failures.append(entry)
        logger.info("Network failure [%s] %s: %s", request.method, url[:100], failure_text)

    def _handle_response(self, response: Response) -> None:
        """Handle an HTTP response — capture 4xx/5xx status codes."""
        url = response.url
        status = response.status

        if status not in _ERROR_STATUS_CODES:
            return

        if self._should_ignore(url):
            return

        resource_type = response.request.resource_type
        if resource_type not in _MONITORED_RESOURCE_TYPES:
            return

        entry = {
            "type": "http_error",
            "url": url,
            "method": response.request.method,
            "resource_type": resource_type,
            "status": status,
            "status_text": response.status_text,
            "error": f"HTTP {status} {response.status_text}",
        }
        self._failures.append(entry)
        logger.info("HTTP error [%d] %s %s", status, response.request.method, url[:100])

    def get_failures(self) -> list[dict[str, Any]]:
        """Return all captured network failures."""
        return list(self._failures)

    def clear(self) -> None:
        """Clear recorded failures."""
        self._failures.clear()
