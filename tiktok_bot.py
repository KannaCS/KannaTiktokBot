import asyncio
import logging
import random
import time
import os
from collections import deque

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent,
    DisconnectEvent,
    CommentEvent,
    GiftEvent,
    LikeEvent,
    JoinEvent,
    LiveEndEvent,
)

import ai_responder
from config import (
    TIKTOK_USERNAME,
    COMMENT_MIN_INTERVAL,
    COMMENT_MAX_INTERVAL,
    REPLY_TO_COMMENTS,
    MAX_REPLIES_PER_MINUTE,
    PLAYWRIGHT_HEADLESS,
)
from tiktok_poster import TikTokPoster

logger = logging.getLogger(__name__)


class TikTokBot:
    def __init__(self):
        session_id = os.getenv("TIKTOK_SESSION_ID", "")

        # TikTokLive client — read-only event stream
        self.client = TikTokLiveClient(unique_id=f"@{TIKTOK_USERNAME}")

        if session_id:
            self.client.web.headers["Cookie"] = f"sessionid={session_id}"
            logger.info("✅ Session cookie di-inject ke TikTokLive client")
        else:
            logger.warning(
                "⚠️  TIKTOK_SESSION_ID kosong — event stream mungkin diblokir dari cloud"
            )

        # Playwright poster — actually sends comments via a real browser
        self.poster = TikTokPoster(
            username=TIKTOK_USERNAME,
            session_id=session_id,
            headless=PLAYWRIGHT_HEADLESS,
        )

        self.is_running = False

        # Rate limiting
        self.last_comment_time = 0
        self.reply_timestamps: deque = deque()

        # Register event handlers
        self._register_events()

    def _register_events(self):
        """Daftarkan semua event handler."""

        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            logger.info(f"✅ Terhubung ke live @{TIKTOK_USERNAME}!")
            self.is_running = True
            asyncio.create_task(self._auto_comment_loop())

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            logger.info("❌ Terputus dari live.")
            self.is_running = False

        @self.client.on(LiveEndEvent)
        async def on_live_end(event: LiveEndEvent):
            logger.info("🔴 Live telah berakhir.")
            self.is_running = False

        @self.client.on(JoinEvent)
        async def on_join(event: JoinEvent):
            try:
                username = event.user.nickname or event.user.unique_id
            except Exception:
                username = "someone"
            ai_responder.update_context("JOIN", f"{username} baru masuk live")
            logger.debug(f"➕ {username} joined")

        @self.client.on(LikeEvent)
        async def on_like(event: LikeEvent):
            try:
                username = event.user.nickname or event.user.unique_id
            except Exception:
                username = "someone"
            ai_responder.update_context("LIKE", f"{username} kasih like")
            logger.debug(f"❤️ {username} liked")

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            try:
                username = event.user.nickname or event.user.unique_id
            except Exception:
                username = "someone"
            comment = event.comment

            logger.info(f"💬 [{username}]: {comment}")
            ai_responder.add_comment_to_context(username, comment)

            if REPLY_TO_COMMENTS and self._can_reply():
                if random.random() < 0.30:
                    asyncio.create_task(self._delayed_reply(username, comment))

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            try:
                streakable = getattr(event.gift, "streakable", False)
                streak_ending = getattr(event, "streak_ending", True)
                if streakable and not streak_ending:
                    return

                username = event.user.nickname or event.user.unique_id
                gift_name = getattr(event.gift, "name", "gift")
                repeat = getattr(event, "repeat_count", 1) or 1

                logger.info(f"🎁 {username} sent {gift_name} x{repeat}")
                ai_responder.update_context("GIFT", f"{username} kasih {gift_name} x{repeat}")

                if random.random() < 0.70 and self._can_comment():
                    asyncio.create_task(self._send_gift_reaction(username, gift_name, repeat))
            except Exception as e:
                logger.debug(f"Gift event error: {e}")

    # ------------------------------------------------------------------
    # Rate-limiting helpers
    # ------------------------------------------------------------------

    def _can_comment(self) -> bool:
        elapsed = time.time() - self.last_comment_time
        return elapsed >= COMMENT_MIN_INTERVAL

    def _can_reply(self) -> bool:
        now = time.time()
        while self.reply_timestamps and now - self.reply_timestamps[0] > 60:
            self.reply_timestamps.popleft()
        return len(self.reply_timestamps) < MAX_REPLIES_PER_MINUTE

    def _record_comment(self):
        self.last_comment_time = time.time()

    def _record_reply(self):
        self.reply_timestamps.append(time.time())
        self._record_comment()

    # ------------------------------------------------------------------
    # Comment generation tasks
    # ------------------------------------------------------------------

    async def _auto_comment_loop(self):
        logger.info("🤖 Auto-comment loop dimulai.")
        await asyncio.sleep(random.uniform(10, 30))

        while self.is_running:
            try:
                comment = await ai_responder.generate_live_comment()
                if comment:
                    await self._post_comment(comment)
                    self._record_comment()

                wait_time = random.uniform(COMMENT_MIN_INTERVAL, COMMENT_MAX_INTERVAL)
                logger.debug(f"⏳ Tunggu {wait_time:.0f}s sebelum komentar berikutnya...")
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error di auto-comment loop: {e}")
                await asyncio.sleep(30)

        logger.info("🛑 Auto-comment loop berhenti.")

    async def _delayed_reply(self, username: str, comment: str):
        await asyncio.sleep(random.uniform(1, 5))
        reply = await ai_responder.generate_reply(username, comment)
        if reply and self._can_reply():
            await self._post_comment(reply)
            self._record_reply()

    async def _send_gift_reaction(self, username: str, gift_name: str, repeat: int):
        await asyncio.sleep(random.uniform(2, 8))
        reaction = await ai_responder.generate_gift_reaction(username, gift_name, repeat)
        if reaction and self._can_comment():
            await self._post_comment(reaction)
            self._record_comment()

    # ------------------------------------------------------------------
    # Actual comment posting (via Playwright)
    # ------------------------------------------------------------------

    async def _post_comment(self, text: str):
        """Send a comment to TikTok Live chat via the Playwright browser."""
        success = await self.poster.post_comment(text)
        if not success:
            logger.warning(f"⚠️  Komentar gagal terkirim: {text}")

    # ------------------------------------------------------------------
    # Bot lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        logger.info(f"🚀 Menghubungkan ke live @{TIKTOK_USERNAME}...")

        # Start the Playwright browser first so it's ready when comments are needed
        await self.poster.start()

        try:
            await self.client.start()
        except Exception as e:
            logger.error(f"Gagal connect ke TikTokLive: {e}")
            raise

    async def stop(self):
        self.is_running = False
        try:
            await self.client.disconnect()
        except Exception:
            pass
        await self.poster.stop()
        logger.info("Bot dihentikan.")
