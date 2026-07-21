"""
TikTok comment poster via Playwright.

Opens TikTok Live in a real Chromium browser using stored cookies,
then types and submits comments into the live chat input box.
This bypasses bot-detection that blocks direct API/HTTP approaches.
"""

import asyncio
import logging
import os
import json
import time
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Selectors — TikTok changes these occasionally; update if things break.
# ---------------------------------------------------------------------------
CHAT_INPUT_SELECTOR = 'div[data-e2e="chat-input"], div[contenteditable="true"][placeholder]'
SEND_BUTTON_SELECTOR = 'button[data-e2e="chat-send-btn"], button[data-e2e="comment-post-btn"]'

# Fallback: press Enter to submit if the send button isn't found
SUBMIT_VIA_ENTER = True


class TikTokPoster:
    """
    Manages a Playwright browser session that stays open for the duration
    of the bot run and posts comments to TikTok Live chat.
    """

    def __init__(
        self,
        username: str,
        session_id: str,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
    ):
        self.username = username.lstrip("@")
        self.session_id = session_id
        self.headless = headless
        # Persistent context directory lets Playwright reuse login state
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.dirname(__file__), ".playwright_profile"
        )

        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._ready = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        """Launch browser and navigate to the live page."""
        logger.info("🌐 Memulai Playwright browser...")
        self._playwright = await async_playwright().start()

        # Use a persistent context so cookies / localStorage survive restarts
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
        )

        # Inject session cookie so TikTok sees us as logged in
        if self.session_id:
            await self._context.add_cookies(
                [
                    {
                        "name": "sessionid",
                        "value": self.session_id,
                        "domain": ".tiktok.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "None",
                    }
                ]
            )
            logger.info("🍪 Session cookie TikTok di-inject.")
        else:
            logger.warning(
                "⚠️  TIKTOK_SESSION_ID kosong — bot tidak akan bisa posting komentar."
            )

        self._page = await self._context.new_page()

        # Mask navigator.webdriver so TikTok's JS fingerprinting doesn't flag us
        await self._page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        live_url = f"https://www.tiktok.com/@{self.username}/live"
        logger.info(f"🔗 Navigasi ke {live_url}")
        await self._page.goto(live_url, wait_until="domcontentloaded", timeout=30_000)

        # Wait for the chat input to appear — means the live page loaded
        try:
            await self._page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=20_000)
            self._ready = True
            logger.info("✅ Live page siap — chat input ditemukan.")
        except Exception:
            logger.warning(
                "⚠️  Chat input tidak ditemukan dalam 20 detik. "
                "Live mungkin belum mulai atau selector berubah."
            )
            # Still mark ready so the bot can retry later
            self._ready = True

    async def stop(self):
        """Close the browser cleanly."""
        self._ready = False
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Playwright cleanup error: {e}")
        logger.info("🛑 Playwright browser ditutup.")

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    async def post_comment(self, text: str) -> bool:
        """
        Type and submit *text* into the TikTok Live chat.

        Returns True on success, False on failure.
        """
        if not self._ready or not self._page:
            logger.warning("Poster belum siap — skip komentar.")
            return False

        async with self._lock:
            try:
                return await self._do_post(text)
            except Exception as e:
                logger.error(f"❌ Gagal post komentar via Playwright: {e}")
                await self._try_recover()
                return False

    async def _do_post(self, text: str) -> bool:
        page = self._page

        # Re-check page is still on the live URL (handles navigation errors)
        if "live" not in page.url:
            logger.info("📄 Halaman berpindah — navigasi ulang ke live...")
            live_url = f"https://www.tiktok.com/@{self.username}/live"
            await page.goto(live_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=15_000)

        # Find chat input
        chat_input = page.locator(CHAT_INPUT_SELECTOR).first
        await chat_input.wait_for(state="visible", timeout=10_000)
        await chat_input.click()
        await asyncio.sleep(0.3)

        # Clear any existing text then type our comment
        await chat_input.fill("")
        await asyncio.sleep(0.1)

        # Type character by character with small delays to mimic human input
        for char in text:
            await chat_input.type(char, delay=30)

        await asyncio.sleep(0.3)

        # Try clicking send button first; fall back to Enter key
        sent = False
        try:
            send_btn = page.locator(SEND_BUTTON_SELECTOR).first
            if await send_btn.is_visible(timeout=2_000):
                await send_btn.click()
                sent = True
        except Exception:
            pass

        if not sent and SUBMIT_VIA_ENTER:
            await chat_input.press("Enter")
            sent = True

        if sent:
            logger.info(f"✅ Komentar terkirim: {text}")
        return sent

    async def _try_recover(self):
        """Best-effort attempt to reload the live page after an error."""
        try:
            logger.info("🔄 Mencoba reload live page...")
            live_url = f"https://www.tiktok.com/@{self.username}/live"
            await self._page.goto(live_url, wait_until="domcontentloaded", timeout=30_000)
            await self._page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=15_000)
            logger.info("✅ Live page berhasil di-reload.")
        except Exception as e:
            logger.error(f"Recovery gagal: {e}")
