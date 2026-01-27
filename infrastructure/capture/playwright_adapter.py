from pathlib import Path
from playwright.async_api import async_playwright
from ...domain.ports.capture_port import UrlCapturePort

class PlaywrightAdapter(UrlCapturePort):
    async def capture(self, url: str, destination_dir: str) -> None:
        path_dir = Path(destination_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 2560, 'height': 1440}, ignore_https_errors=True)
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception:
                pass 
            
            cdp = await context.new_cdp_session(page)
            mhtml = (await cdp.send("Page.captureSnapshot", {"format": "mhtml"})).get("data")
            with open(path_dir / "page.mhtml", "w", encoding="utf-8") as f: f.write(mhtml)
            
            await page.screenshot(path=str(path_dir / "page_screenshot.png"), full_page=True)
            await page.pdf(path=str(path_dir / "page_print.pdf"))
            await browser.close()