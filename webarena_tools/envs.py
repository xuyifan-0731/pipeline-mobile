from __future__ import annotations

import json
from pathlib import Path
from playwright.sync_api import (
    sync_playwright,
    Playwright,
    Page,
    BrowserContext
)

from .constants import DEFAULT_VIEWPORT

def setup(
    playwright: Playwright,
    config_file: Path | None = None,
    options: dict[str, str] | None = None,
) -> tuple[BrowserContext, Page]:
    slow_mo = options.get("slow_mo", 0)
    viewport = options.get("viewport", DEFAULT_VIEWPORT)
    
    browser = playwright.chromium.launch(
        headless=True, slow_mo=slow_mo
    )

    if config_file:
        with open(config_file, "r") as f:
            instance_config = json.load(f)
    else:
        instance_config = {}

    storage_state = instance_config.get("storage_state", None)
    start_url = instance_config.get("start_url", None)
    geolocation = instance_config.get("geolocation", None)

    context = browser.new_context(
        viewport=viewport,
        storage_state=storage_state,
        geolocation=geolocation,
        device_scale_factor=1,
    )
    
    if start_url:
        start_urls = start_url.split(" |AND| ")
        for url in start_urls:
            page = context.new_page()
            page.goto(url)
        # set the first page as the current page
        page = context.pages[0]
        page.bring_to_front()
    else:
        page = context.new_page()
    
    return context, page