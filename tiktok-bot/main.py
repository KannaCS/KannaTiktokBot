"""
TikTok Live Bot
Menonton live TikTok dan berkomentar secara otomatis menggunakan AI.

Cara pakai:
    python main.py
"""

import asyncio
import logging
import signal
import sys

from config import validate_config
from tiktok_bot import TikTokBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    # Validasi config
    try:
        validate_config()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    bot = TikTokBot()

    # Handle Ctrl+C dan SIGTERM (untuk systemd)
    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("Menerima sinyal shutdown...")
        asyncio.create_task(bot.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            # Windows tidak support add_signal_handler
            pass

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Dihentikan oleh user.")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
