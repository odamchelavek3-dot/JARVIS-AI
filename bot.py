
import os
import asyncio
import logging
import threading

from dotenv import load_dotenv
from groq import Groq
from flask import Flask

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "openai/gpt-oss-20b"

if not BOT_TOKEN or not GROQ_API_KEY:
    raise ValueError("BOT_TOKEN yoki GROQ_API_KEY topilmadi!")

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

web = Flask(__name__)

@web.route("/")
def home():
    return "JARVIS AI is running!"

@web.route("/health")
def health():
    return {"status": "ok", "bot": "JARVIS"}

def start_web_server():
    port = int(os.getenv("PORT", "10000"))
    web.run(host="0.0.0.0", port=port, use_reloader=False)

user_histories = {}

SYSTEM_PROMPT = """
Sen JARVIS nomli aqlli virtual yordamchisan.
- Tabiiy va tushunarli tilda javob ber.
- Asosan o'zbek tilida gaplash.
- Boshqa tilda yozilsa, o'sha tilda javob ber.
- Aqlli, xushmuomala va professional bo'l.
- Savollarga aniq va foydali javob ber.
- Bilmagan narsangni to'qib chiqarmagin.
"""

MAX_HISTORY = 12

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 Assalomu alaykum, {user.first_name}!\n\n"
        "Men JARVIS — sizning AI yordamchingizman.\n\n"
        "🧠 AI bilan suhbat\n"
        "💬 Savollarga javob\n"
        "🌍 Tarjima\n"
        "💻 Dasturlashda yordam\n\n"
        "/clear — Xotirani tozalash\n"
        "/help — Yordam"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 JARVIS YORDAM\n\n"
        "Istalgan savolingizni yozing.\n"
        "/start — Boshlash\n"
        "/clear — Xotirani tozalash\n"
        "/help — Yordam"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("🧹 Suhbat xotirasi tozalandi!")

def ask_groq(messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_completion_tokens=1200
    )
    return response.choices[0].message.content or "Javob olinmadi."

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if not user_text:
        return

    history = user_histories.setdefault(user_id, [])
    history.append({"role": "user", "content": user_text})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history[-MAX_HISTORY:]

    try:
        await update.message.chat.send_action(ChatAction.TYPING)

        answer = await asyncio.to_thread(ask_groq, messages)

        history.append({"role": "assistant", "content": answer})
        user_histories[user_id] = history[-MAX_HISTORY:]

        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i + 4000])

    except Exception:
        if history and history[-1]["role"] == "user":
            history.pop()

        logger.exception("JARVIS AI xatoligi")

        await update.message.reply_text(
            "⚠️ Hozircha javob bera olmadim. Keyinroq urinib ko'ring."
        )

def main():
    threading.Thread(target=start_web_server, daemon=True).start()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
    )

    print("🤖 JARVIS AI ishga tushdi!")

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
