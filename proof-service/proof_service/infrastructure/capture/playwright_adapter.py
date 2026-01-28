import base64
from pathlib import Path
from playwright.async_api import async_playwright
from ...domain.ports.capture_port import UrlCapturePort

class PlaywrightAdapter(UrlCapturePort):
    def __init__(
        self,
        nav_timeout_ms: int = 60000,
        wait_after_ms: int = 5000,
        wait_selector: str = "article",
        headless: bool = True,
    ):
        self.nav_timeout_ms = nav_timeout_ms
        self.wait_after_ms = wait_after_ms
        self.wait_selector = wait_selector
        self.headless = headless

    async def capture(self, url: str, destination_dir: str) -> None:
        path_dir = Path(destination_dir)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                page.set_default_navigation_timeout(self.nav_timeout_ms)
                page.set_default_timeout(self.nav_timeout_ms)
                await page.goto(url, wait_until="domcontentloaded")
                try:
                    if self.wait_selector:
                        await page.wait_for_selector(self.wait_selector, timeout=15000)
                except Exception:
                    pass
                await page.wait_for_timeout(self.wait_after_ms)
                # Scroll to trigger lazy loading (images/videos)
                await page.evaluate(
                    """
                    async () => {
                      const distance = 800;
                      const delay = 200;
                      const maxScrolls = 20;
                      for (let i = 0; i < maxScrolls; i++) {
                        window.scrollBy(0, distance);
                        await new Promise(r => setTimeout(r, delay));
                      }
                      window.scrollTo(0, 0);
                    }
                    """
                )
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                try:
                    await page.emulate_media(media="screen")
                except Exception:
                    pass
            except Exception:
                pass 
            
            screenshot_path = path_dir / "page_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # Build a PDF and HTML from the screenshot so it matches what we see visually.
            try:
                img_b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
                html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Proof Capture</title>
    <style>
      body {{ margin: 0; font-family: Arial, sans-serif; background: #111; color: #fff; }}
      .meta {{ padding: 16px; background: #1b1b1b; }}
      .meta a {{ color: #4ea1ff; }}
      img {{ width: 100%; height: auto; display: block; }}
    </style>
  </head>
  <body>
    <div class="meta">
      <div><strong>URL:</strong> <a href="{url}">{url}</a></div>
    </div>
    <img src="data:image/png;base64,{img_b64}" />
  </body>
</html>
"""
                with open(path_dir / "page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                pdf_page = await context.new_page()
                await pdf_page.set_content(html, wait_until="load")
                await pdf_page.pdf(
                    path=str(path_dir / "page_print.pdf"),
                    print_background=True,
                    prefer_css_page_size=True,
                )
                await pdf_page.close()
            except Exception:
                # Fallback to the regular PDF if image-based rendering fails.
                await page.pdf(
                    path=str(path_dir / "page_print.pdf"),
                    print_background=True,
                    prefer_css_page_size=True,
                )
            await browser.close()
