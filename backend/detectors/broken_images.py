"""
BugHunter — Bug Detector: Broken Images
Ported from qa-agent/src/tools/broken-images.ts (crislerwin/qa-agent)

Detects images with failed loads, missing src, zero dimensions.
"""
from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_BROKEN_IMAGE_JS = """
async () => {
    const images = Array.from(document.querySelectorAll('img'));
    const results = [];

    for (const img of images) {
        const src = img.getAttribute('src') || img.src || '';
        const alt = img.alt || '';
        const selector = img.id ? '#' + img.id : (img.className ? '.' + img.className.split(' ')[0] : 'img');
        const naturalWidth = img.naturalWidth;
        const naturalHeight = img.naturalHeight;
        const complete = img.complete;

        // Missing src
        if (!src) {
            results.push({
                type: 'missing_src',
                selector: selector,
                alt: alt,
                src: '',
                reason: 'Image has no src attribute'
            });
            continue;
        }

        // Skip data: URIs and SVG (valid inline)
        if (src.startsWith('data:') || src.startsWith('blob:')) {
            continue;
        }

        // Check if loaded — complete=true, naturalWidth=0 means broken
        if (complete && naturalWidth === 0 && naturalHeight === 0) {
            // Exclude tracking pixels (1x1 intentionally tiny images)
            const isTrackingPixel = naturalWidth <= 1 && naturalHeight <= 1 &&
                (src.includes('track') || src.includes('pixel') || src.includes('beacon'));
            if (!isTrackingPixel) {
                results.push({
                    type: 'broken_image',
                    selector: selector,
                    alt: alt,
                    src: src,
                    reason: 'Image failed to load (naturalWidth=0, complete=true)'
                });
            }
        }

        // Check for non-http URLs that are broken references
        if (!complete) {
            results.push({
                type: 'loading_failed',
                selector: selector,
                alt: alt,
                src: src,
                reason: 'Image did not complete loading'
            });
        }
    }

    return results;
}
"""


async def find_broken_images(page: Page) -> list[dict[str, Any]]:
    """
    Scan current page for broken, missing, or unloaded images.

    Args:
        page: Current Playwright page

    Returns:
        List of dicts with type, selector, alt, src, reason fields
    """
    try:
        results: list[dict[str, Any]] = await page.evaluate(_BROKEN_IMAGE_JS)
        if results:
            logger.info("Found %d broken image(s) on %s", len(results), page.url)
        return results
    except Exception as exc:
        logger.warning("Broken image detection failed on %s: %s", page.url, exc)
        return []
