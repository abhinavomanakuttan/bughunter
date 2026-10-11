"""
BugHunter — Bug Detector: Validation Errors
Ported from qa-agent/src/tools/validation-errors.ts (crislerwin/qa-agent)

Detects form validation errors and visible error messages on pages.
"""
from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_VALIDATION_SCAN_JS = r"""
() => {
    const results = [];

    // CSS classes and attributes commonly used for error states
    const errorSelectors = [
        '[class*="error"]:not(script)',
        '[class*="invalid"]:not(script)',
        '[class*="alert-danger"]',
        '[class*="alert-error"]',
        '[role="alert"]',
        '.field-error',
        '.form-error',
        '.validation-message',
        '[aria-invalid="true"]',
        'input:invalid',
        'select:invalid',
        'textarea:invalid',
    ];

    const seen = new Set();

    for (const selector of errorSelectors) {
        try {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                // Skip hidden elements
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                    continue;
                }

                const text = (el.textContent || '').trim();
                if (!text || text.length < 3) continue;

                // Deduplicate by text content
                if (seen.has(text.toLowerCase())) continue;
                seen.add(text.toLowerCase());

                const elSelector = el.id ? '#' + el.id :
                    (el.className ? '.' + el.className.trim().split(/\s+/)[0] : el.tagName.toLowerCase());

                results.push({
                    selector: elSelector,
                    text: text.substring(0, 500),
                    matched_by: selector,
                    tag: el.tagName.toLowerCase(),
                    aria_invalid: el.getAttribute('aria-invalid'),
                });
            }
        } catch(e) {
            // Ignore selector errors
        }
    }

    // Also look for browser native validation messages
    const invalidInputs = Array.from(document.querySelectorAll('input, select, textarea')).filter(el => {
        return el.validity && !el.validity.valid && el.validationMessage;
    });

    for (const input of invalidInputs) {
        const msg = input.validationMessage;
        if (!msg || seen.has(msg.toLowerCase())) continue;
        seen.add(msg.toLowerCase());

        results.push({
            selector: input.id ? '#' + input.id : input.name ? '[name="' + input.name + '"]' : input.tagName.toLowerCase(),
            text: msg,
            matched_by: 'browser_native_validation',
            tag: input.tagName.toLowerCase(),
            aria_invalid: 'true',
        });
    }

    return results;
}
"""


async def find_validation_errors(page: Page) -> list[dict[str, Any]]:
    """
    Scan current page for visible validation errors and invalid form fields.

    Args:
        page: Current Playwright page

    Returns:
        List of dicts with selector, text, matched_by, tag, aria_invalid fields
    """
    try:
        results: list[dict[str, Any]] = await page.evaluate(_VALIDATION_SCAN_JS)
        if results:
            logger.info("Found %d validation error(s) on %s", len(results), page.url)
        return results
    except Exception as exc:
        logger.warning("Validation error detection failed on %s: %s", page.url, exc)
        return []
