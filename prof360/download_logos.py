#!/usr/bin/env python3
"""
Download all company logos from a JavaScript-rendered page.

The target page renders its content client-side, so we use Playwright
(a headless browser) instead of plain requests.

Setup:
    pip install playwright
    playwright install chromium

Usage:
    python download_logos.py
"""

import os
import re
import base64
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

URL = "https://www.pulserobotics.com/finance/sp500"
OUT_DIR = "logos"


def safe_name(url_or_name: str, fallback_idx: int) -> str:
    """Build a filesystem-safe filename from a URL or alt text."""
    name = os.path.basename(urlparse(url_or_name).path) or f"logo_{fallback_idx}"
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not os.path.splitext(name)[1]:
        name += ".png"
    return name


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60_000)

        # Give any lazy-loaded content a moment. Scroll to trigger lazy images.
        page.wait_for_timeout(2000)
        page.evaluate("""
            async () => {
                for (let y = 0; y < document.body.scrollHeight; y += 800) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 200));
                }
            }
        """)
        page.wait_for_timeout(1500)

        # Collect image sources: <img src>, <img data-src>, and CSS backgrounds.
        sources = page.evaluate("""
            () => {
                const urls = new Set();
                document.querySelectorAll('img').forEach(img => {
                    const s = img.currentSrc || img.src || img.getAttribute('data-src');
                    if (s) urls.add(s);
                });
                document.querySelectorAll('*').forEach(el => {
                    const bg = getComputedStyle(el).backgroundImage;
                    const m = bg && bg.match(/url\\(["']?(.*?)["']?\\)/);
                    if (m && m[1]) urls.add(m[1]);
                });
                return [...urls];
            }
        """)

        request_context = page.context.request
        print(f"Found {len(sources)} candidate image URLs")

        for i, src in enumerate(sources):
            try:
                if src.startswith("data:"):
                    # Inline base64 image.
                    header, b64 = src.split(",", 1)
                    ext = "png"
                    m = re.search(r"data:image/(\w+)", header)
                    if m:
                        ext = m.group(1).split("+")[0]
                    path = os.path.join(OUT_DIR, f"logo_{i}.{ext}")
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(b64))
                else:
                    abs_url = urljoin(URL, src)
                    resp = request_context.get(abs_url)
                    if not resp.ok:
                        print(f"  skip {abs_url} ({resp.status})")
                        continue
                    path = os.path.join(OUT_DIR, safe_name(abs_url, i))
                    with open(path, "wb") as f:
                        f.write(resp.body())
                print(f"  saved {path}")
            except Exception as e:
                print(f"  error on {src[:80]}: {e}")

        browser.close()
    print(f"\nDone. Logos saved to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
