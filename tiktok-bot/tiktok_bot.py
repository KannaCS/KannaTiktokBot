import asyncio
import logging
import random
import time
from collections import deque

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent,
    DisconnectEvent,
    CommentEvent,
    GiftEvent,
    LikeEvent,
    JoinEvent,
    ViewerCountUpdateEvent,
    LiveEndEvent,
)

import ai_responder
from config import (
    TIKTOK_USERNAME,
    COMMENT_MIN_INTERVAL,
    COMMENT_MAX_INTERVAL,
    REPLY_TO_COMMENTS,
    MAX_REPLIES_PER_MINUTE,
)

logger = logging.getLogger(__name__)


class TikTokBot:
    def __init__(self):
        self.client = TikTokLiveClient(unique_id=f"@{TIKTOK_USERNAME}")
        self.is_running = False

        # Rate limiting
        self.last_comment_time = 0
        self.reply_timestamps = deque()  # Track waktu reply untuk rate limiting

        # Register event handlers
        self._register_events()

    def _register_events(self):
        """Daftarkan semua event handler."""

        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            logger.info(f"✅ Terhubung ke live @{TIKTOK_USERNAME}!")
            self.is_running = True
            # Mulai loop komentar otomatis
            asyncio.create_task(self._auto_comment_loop())

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            logger.info("❌ Terputus dari live.")
            self.is_running = False

        @self.client.on(LiveEndEvent)
        async def on_live_end(event: LiveEndEvent):
            logger.info("🔴 Live telah berakhir.")
            self.is_running = False

        @self.client.on(ViewerCountUpdateEvent)
        async def on_viewer_update(event: ViewerCountUpdateEvent):
            ai_responder.set_viewer_count(event.viewer_count)
            logger.debug(f"👁️ Viewers: {event.viewer_count}")

        @self.client.on(JoinEvent)
        async def on_join(event: JoinEvent):
            username = event.user.nickname or event.user.unique_id
            ai_responder.update_context("JOIN", f"{username} baru masuk live")
            logger.debug(f"➕ {username} joined")

        @self.client.on(LikeEvent)
        async def on_like(event: LikeEvent):
            username = event.user.nickname or event.user.unique_id
            ai_responder.update_context("LIKE", f"{username} kasih like")
            logger.debug(f"❤️ {username} liked")

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            username = event.user.nickname or event.user.unique_id
            comment = event.comment

            logger.info(f"💬 [{username}]: {comment}")

            # Tambah ke konteks
            ai_responder.add_comment_to_context(username, comment)

            # Putuskan apakah perlu balas
            if REPLY_TO_COMMENTS and self._can_reply():
                # Balas dengan probabilitas 30% supaya tidak terlalu agresif
                if random.random() < 0.30:
                    asyncio.create_task(self._delayed_reply(username, comment))

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            # Hanya proses gift yang sudah selesai (streak_ended)
            if not event.gift.streakable or event.gift.streak_ending:
                username = event.user.nickname or event.user.unique_id
                gift_name = event.gift.name
                repeat = event.repeat_count or 1

                logger.info(f"🎁 {username} sent {gift_name} x{repeat}")
                ai_responder.update_context("GIFT", f"{username} kasih {gift_name} x{repeat}")

                # Reaksi gift dengan probabilitas 70%
                if random.random() < 0.70 and self._can_comment():
                    asyncio.create_task(self._send_gift_reaction(username, gift_name, repeat))

    def _can_comment(self) -> bool:
        """Cek apakah sudah cukup jeda dari komentar terakhir."""
        elapsed = time.time() - self.last_comment_time
        return elapsed >= COMMENT_MIN_INTERVAL

    def _can_reply(self) -> bool:
        """Cek rate limit untuk reply (max N reply per menit)."""
        now = time.time()
        # Buang timestamp yang lebih dari 60 detik
        while self.reply_timestamps and now - self.reply_timestamps[0] > 60:
            self.reply_timestamps.popleft()
        return len(self.reply_timestamps) < MAX_REPLIES_PER_MINUTE

    def _record_comment(self):
        """Catat waktu komentar terakhir."""
        self.last_comment_time = time.time()

    def _record_reply(self):
        """Catat waktu reply untuk rate limiting."""
        self.reply_timestamps.append(time.time())
        self._record_comment()

    async def _auto_comment_loop(self):
        """
        Loop utama yang generate komentar otomatis secara berkala.
        Berjalan selama live aktif.
        """
        logger.info("🤖 Auto-comment loop dimulai.")

        # Tunggu sebentar dulu sebelum komentar pertama
        await asyncio.sleep(random.uniform(10, 30))

        while self.is_running:
            try:
                comment = await ai_responder.generate_live_comment()
                if comment:
                    await self._post_comment(comment)

                # Tunggu interval acak sebelum komentar berikutnya
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
        """Reply ke komentar dengan delay natural (1-5 detik)."""
        await asyncio.sleep(random.uniform(1, 5))
        reply = await ai_responder.generate_reply(username, comment)
        if reply and self._can_reply():
            await self._post_comment(reply)
            self._record_reply()

    async def _send_gift_reaction(self, username: str, gift_name: str, repeat: int):
        """Kirim reaksi gift setelah delay singkat."""
        await asyncio.sleep(random.uniform(2, 8))
        reaction = await ai_responder.generate_gift_reaction(username, gift_name, repeat)
        if reaction and self._can_comment():
            await self._post_comment(reaction)
            self._record_comment()

    async def _post_comment(self, text: str):
        """
        Post komentar ke TikTok Live.
        
        CATATAN: TikTokLive library versi terbaru adalah READ-ONLY (hanya bisa baca event).
        Untuk posting komentar, kamu perlu TikTok API resmi atau solusi alternatif.
        Lihat README.md untuk penjelasan lebih lanjut.
        """
        logger.info(f"📤 [BOT COMMENT]: {text}")
        # TODO: Implementasi posting komentar (lihat README.md)
        # Opsi 1: TikTok Creator API (butuh approval)
        # Opsi 2: Selenium/browser automation (tidak disarankan untuk produksi)
        # Opsi 3: Third-party service seperti Ayrshare

    async def start(self):
        """Mulai koneksi ke live."""
        logger.info(f"🚀 Menghubungkan ke live @{TIKTOK_USERNAME}...")
        try:
            await self.client.start()
        except Exception as e:
            logger.error(f"Gagal connect: {e}")
            raise

    async def stop(self):
        """Hentikan bot."""
        self.is_running = False
        await self.client.disconnect()
        logger.info("Bot dihentikan.")
