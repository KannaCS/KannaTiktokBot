import os
from dotenv import load_dotenv

load_dotenv()

# TikTok config
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", "")

# Groq config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Bot persona
BOT_PERSONA_NAME = os.getenv("BOT_PERSONA_NAME", "Andi")
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "id")

# Timing config
COMMENT_MIN_INTERVAL = int(os.getenv("COMMENT_MIN_INTERVAL", "30"))
COMMENT_MAX_INTERVAL = int(os.getenv("COMMENT_MAX_INTERVAL", "90"))

# Interaction config
REPLY_TO_COMMENTS = os.getenv("REPLY_TO_COMMENTS", "true").lower() == "true"
MAX_REPLIES_PER_MINUTE = int(os.getenv("MAX_REPLIES_PER_MINUTE", "2"))

# Playwright config
# Set PLAYWRIGHT_HEADLESS=false to see the browser window (useful for debugging)
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

# System prompt untuk AI
SYSTEM_PROMPT_ID = f"""Kamu adalah {BOT_PERSONA_NAME}, seorang penonton setia TikTok Live yang antusias dan ramah.
Kamu sedang menonton live streaming dan berkomentar secara natural seperti penonton biasa.

Aturan penting:
- Komentar harus singkat, maksimal 2 kalimat
- Gunakan bahasa Indonesia yang santai dan gaul (boleh pakai "wkwk", "anjir", "gokil", dll)
- Jangan pernah bilang kamu adalah bot atau AI
- Bereaksi natural terhadap apa yang terjadi di live
- Kadang pakai emoji yang relevan
- Jangan spam atau terlalu berlebihan
- Variasikan gaya komentar supaya terlihat natural
"""

SYSTEM_PROMPT_EN = f"""You are {BOT_PERSONA_NAME}, an enthusiastic and friendly TikTok Live viewer.
You are watching a live stream and commenting naturally like a regular viewer.

Important rules:
- Keep comments short, max 2 sentences
- Use casual, natural language
- Never admit you are a bot or AI
- React naturally to what's happening in the live
- Sometimes use relevant emojis
- Don't spam or be over the top
- Vary your comment style to seem natural
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_ID if BOT_LANGUAGE == "id" else SYSTEM_PROMPT_EN

def validate_config():
    """Validasi konfigurasi yang wajib ada."""
    errors = []
    if not TIKTOK_USERNAME:
        errors.append("TIKTOK_USERNAME belum diisi di .env")
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY belum diisi di .env")
    if errors:
        raise ValueError("Config error:\n" + "\n".join(f"  - {e}" for e in errors))
