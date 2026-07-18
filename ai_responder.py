import asyncio
import logging
from groq import AsyncGroq
from config import GROQ_API_KEY, SYSTEM_PROMPT, BOT_LANGUAGE

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=GROQ_API_KEY)

# Model Groq yang dipakai — llama3-8b-8192 cepat dan gratis tier-nya besar
GROQ_MODEL = "llama3-8b-8192"

# Konteks live yang dikumpulkan selama sesi
live_context = {
    "recent_events": [],      # Event terakhir di live (join, gift, dll)
    "recent_comments": [],    # Komentar terakhir dari penonton lain
    "viewer_count": 0,
}

MAX_CONTEXT_ITEMS = 10  # Batasi memori supaya token tidak membengkak


def update_context(event_type: str, data: str):
    """Tambah event ke konteks live."""
    live_context["recent_events"].append(f"[{event_type}] {data}")
    if len(live_context["recent_events"]) > MAX_CONTEXT_ITEMS:
        live_context["recent_events"].pop(0)


def add_comment_to_context(username: str, comment: str):
    """Simpan komentar penonton ke konteks."""
    live_context["recent_comments"].append(f"{username}: {comment}")
    if len(live_context["recent_comments"]) > MAX_CONTEXT_ITEMS:
        live_context["recent_comments"].pop(0)


def set_viewer_count(count: int):
    live_context["viewer_count"] = count


def _build_context_summary() -> str:
    """Buat ringkasan konteks live untuk dikirim ke AI."""
    parts = []

    if live_context["viewer_count"]:
        parts.append(f"Jumlah penonton saat ini: {live_context['viewer_count']}")

    if live_context["recent_events"]:
        parts.append("Event terbaru di live:\n" + "\n".join(live_context["recent_events"][-5:]))

    if live_context["recent_comments"]:
        parts.append("Komentar penonton terakhir:\n" + "\n".join(live_context["recent_comments"][-5:]))

    return "\n\n".join(parts) if parts else "Live baru dimulai."


async def generate_live_comment() -> str | None:
    """
    Generate komentar spontan sebagai penonton live.
    Dipanggil secara berkala selama live berlangsung.
    """
    context = _build_context_summary()

    if BOT_LANGUAGE == "id":
        user_prompt = f"""Situasi live sekarang:
{context}

Tulis 1 komentar singkat sebagai penonton yang antusias.
Jangan mulai dengan sapaan formal. Langsung ke komentar yang natural."""
    else:
        user_prompt = f"""Current live situation:
{context}

Write 1 short comment as an enthusiastic viewer.
Don't start with formal greetings. Go straight to a natural comment."""

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=100,
            temperature=0.9,
        )
        comment = response.choices[0].message.content.strip()
        logger.info(f"[AI] Generated comment: {comment}")
        return comment
    except Exception as e:
        logger.error(f"[AI] Error generating comment: {e}")
        return None


async def generate_reply(username: str, their_comment: str) -> str | None:
    """
    Generate balasan ke komentar penonton lain.
    """
    context = _build_context_summary()

    if BOT_LANGUAGE == "id":
        user_prompt = f"""Situasi live sekarang:
{context}

Penonton bernama @{username} baru komentar: "{their_comment}"

Balas komentar mereka secara natural dan singkat, seperti sesama penonton yang berinteraksi.
Boleh setuju, nanya balik, atau nambah pendapat. Jangan terlalu formal."""
    else:
        user_prompt = f"""Current live situation:
{context}

A viewer named @{username} just commented: "{their_comment}"

Reply to their comment naturally and briefly, like a fellow viewer interacting.
You can agree, ask back, or add your opinion. Don't be too formal."""

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=80,
            temperature=0.85,
        )
        reply = response.choices[0].message.content.strip()
        logger.info(f"[AI] Generated reply to {username}: {reply}")
        return reply
    except Exception as e:
        logger.error(f"[AI] Error generating reply: {e}")
        return None


async def generate_gift_reaction(username: str, gift_name: str, repeat_count: int) -> str | None:
    """
    Generate reaksi saat ada yang kasih gift.
    """
    if BOT_LANGUAGE == "id":
        user_prompt = f"""@{username} baru kasih gift '{gift_name}' x{repeat_count} ke streamer!
Tulis 1 reaksi singkat sebagai penonton yang ikut senang/hype. Maksimal 1 kalimat."""
    else:
        user_prompt = f"""@{username} just sent '{gift_name}' x{repeat_count} to the streamer!
Write 1 short reaction as a viewer who's excited. Max 1 sentence."""

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=60,
            temperature=0.9,
        )
        reaction = response.choices[0].message.content.strip()
        logger.info(f"[AI] Gift reaction: {reaction}")
        return reaction
    except Exception as e:
        logger.error(f"[AI] Error generating gift reaction: {e}")
        return None
