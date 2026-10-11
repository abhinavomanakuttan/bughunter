"""
BugHunter — URL Validator with SSRF protection.
Prevents scanning of private networks, cloud metadata endpoints, and localhost
unless DEMO_MODE is enabled explicitly.
"""
from __future__ import annotations

import ipaddress
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private IP ranges (RFC 1918, loopback, link-local, cloud metadata)
_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
]

# Cloud metadata endpoints that should never be accessed
_BLOCKED_HOSTNAMES = {
    "169.254.169.254",   # AWS/GCP/Azure instance metadata
    "metadata.google.internal",
    "metadata.azure.com",
}


class URLValidationError(ValueError):
    """Raised when a URL fails security validation."""


def validate_scan_url(url: str, demo_mode: bool = False) -> str:
    """
    Validate a URL is safe to scan.

    Args:
        url: The target URL to validate
        demo_mode: When True, allows localhost/127.0.0.1 for development

    Returns:
        The validated and normalized URL

    Raises:
        URLValidationError: If the URL fails security checks
    """
    if not url or not isinstance(url, str):
        raise URLValidationError("URL must be a non-empty string")

    url = url.strip()

    # Ensure scheme is present
    if not url.startswith(("http://", "https://")):
        raise URLValidationError(
            f"URL must start with http:// or https:// — got: {url[:50]}"
        )

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise URLValidationError(f"URL parsing failed: {exc}") from exc

    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL must have a valid hostname")

    # Block cloud metadata endpoints
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise URLValidationError(
            f"Blocked: cloud metadata endpoint is forbidden ({hostname})"
        )

    # Check for localhost
    is_localhost = hostname.lower() in ("localhost", "127.0.0.1", "::1") or hostname.startswith("127.")

    if is_localhost and not demo_mode:
        raise URLValidationError(
            "Scanning localhost is only allowed in DEMO_MODE. "
            "Set DEMO_MODE=true in your .env file for local development."
        )

    # Resolve to IP and check if private
    if not is_localhost:
        try:
            ip = ipaddress.ip_address(hostname)
            for private_range in _PRIVATE_RANGES:
                if ip in private_range:
                    raise URLValidationError(
                        f"Blocked: private IP address ({hostname}) cannot be scanned"
                    )
        except ValueError:
            # Not an IP address — it's a domain name, which is allowed
            pass

    # Validate port if present
    port = parsed.port
    if port is not None and (port < 1 or port > 65535):
        raise URLValidationError(f"Invalid port: {port}")

    logger.info("URL validation passed: %s (demo_mode=%s)", url, demo_mode)
    return url
