#!/usr/bin/env python3
"""
Telegram Registration Bot — Simple & Clean
Bilingual (English + አማርኛ) • 7 Separate Steps • No Admin System
"""

import os
import sys
import logging
from datetime import datetime, timezone
from threading import Thread

from flask import Flask
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ══════════════════════════
# SETUP
# ══════════════════════════
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL = os.getenv("ADMIN_CHANNEL_ID", "")
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(format="%(asctime)s | %(message)s", level=logging.INFO)
log = logging.getLogger("bot")

if not TOKEN:
    log.critical("BOT_TOKEN missing!")
    sys.exit(1)

# ══════════════════════════
# FLASK FOR RENDER
# ══════════════════════════
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot Online"

@flask_app.route("/health")
def health():
    return "OK", 200

# ══════════════════════════
# STATES
# ══════════════════════════
FIRST, LAST, MOTHER, CBE, FRONT, BACK, PHOTO = range(7)

# ══════════════════════════
# CONSTANTS
# ══════════════════════════
BTN = "🚀 Start Service | አገልግሎት ጀምር"

# ══════════════════════════
# KEYBOARDS
# ══════════════════════════
def menu():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN)]], resize_keyboard=True)

def hide():
    return ReplyKeyboardRemove()

# ══════════════════════════
# MESSAGES
# ══════════════════════════
WELCOME = (
    "🌟 *Welcome! | እንኳን ደህና መጡ!* 🌟\n\n"
    "_Please complete your registration._\n"
    "_እባክዎ ምዝገባዎን ያጠናቅቁ።_"
)

BEGIN = "📝 *Let's begin! | እንጀምር!*\n\n_Please answer each question._"

STEPS = [
    "1️⃣ *First Name | የመጀመሪያ ስም*\n\n_Enter your first name:_\n_የመጀመሪያ ስምዎን ያስገቡ።_",
    "2️⃣ *Last Name | የአያት ስም*\n\n_Enter your last name:_\n_የአያት ስምዎን ያስገቡ።_",
    "3️⃣ *Mother's Full Name | የእናት ሙሉ ስም*\n\n_Enter your mother's full name:_\n_የእናትዎን ሙሉ ስም ያስገቡ።_",
    "4️⃣ *CBE Account Number | የሲቢኢ አካውንት ቁጥር*\n\n_Enter your CBE Account number:_\n_የሲቢኢ አካውንት ቁጥርዎን ያስገቡ።_",
    "5️⃣ *Front ID | የመታወቂያ ፊት ጎን*\n\n📷 _Upload photo of the FRONT side of your ID:_\n📷 _የመታወቂያዎን የፊት ጎን ፎቶ ያስገቡ።_",
    "6️⃣ *Back ID | የመታወቂያ ጀርባ ጎን*\n\n📷 _Upload photo of the BACK side of your ID:_\n📷 _የመታወቂያዎን የጀርባ ጎን ፎቶ ያስገቡ።_",
    "7️⃣ *Your Photo | የእርስዎ ፎቶ*\n\n📷 _Upload your personal photo:_\n📷 _የራስዎን ፎቶ ያስገቡ።_",
]

ERR_PHOTO = "❌ *Please upload a PHOTO.*\n❌ *እባክዎ ፎቶ ያስገቡ።*"

CANCEL_MSG = "❌ *Cancelled | ተሰርዟል*\n\n_Press Start Service to try again._"

def done(data):
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *You have finished all processes!*\n"
        "✅ *ሁሉንም ሂደቶች አጠናቀዋል!*\n\n"
        "*Please wait while we cross-check:*\n"
        "*እባክዎ እስክንፈትሽ ይጠብቁ:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | ስም:* {data.get('first_name','')}\n"
        f"📋 *Last Name | የአያት ስም:* {data.get('last_name','')}\n"
        f"👩 *Mother | እናት:* {data.get('mothers_name','')}\n"
        f"🏦 *CBE Account | አካውንት:* {data.get('cbe_account','')}\n\n"
        "📷 *Documents Uploaded | የተላኩ ሰነዶች:*\n"
        "• Front ID | ፊት ጎን ✅\n"
        "• Back ID | ጀርባ ጎን ✅\n"
        "• Photo | ፎቶ ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ *_We will review your information shortly._*\n"
        "⏳ *_መረጃዎን በቅርቡ እንመረምራለን።_*"
    )

def channel_msg(data, uid):
    return (
        "📋 *NEW REGISTRATION | አዲስ ምዝገባ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 *User ID:* `{uid}`\n"
        f"📅 *Date:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"📋 *First Name | ስም:* {data.get('first_name','')}\n"
        f"📋 *Last Name | የአያት ስም:* {data.get('last_name','')}\n"
        f"👩 *Mother | እናት:* {data.get('mothers_name','')}\n"
        f"🏦 *CBE | አካውንት:* {data.get('cbe_account','')}\n\n"
        "📷 *Documents Below | ሰነዶች ከዚህ በታች* 👇"
    )

# ══════════════════════════
# HANDLERS
# ══════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start — Show welcome message with button """
    context.user_data.clear()
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=menu())
    log.info(f"/start | User={update.effective_user.id}")
    return ConversationHandler.END


async def btn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ User clicked Start Service button """
    if update.message.text != BTN:
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["reg"] = {}

    await update.message.reply_text(BEGIN, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
    await update.message.reply_text(STEPS[0], parse_mode=ParseMode.MARKDOWN)
    log.info(f"Start Service | User={update.effective_user.id}")
    return FIRST


async def step_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["first_name"] = update.message.text.strip()
    await update.message.reply_text(STEPS[1], parse_mode=ParseMode.MARKDOWN)
    return LAST


async def step_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["last_name"] = update.message.text.strip()
    await update.message.reply_text(STEPS[2], parse_mode=ParseMode.MARKDOWN)
    return MOTHER


async def step_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["mothers_name"] = update.message.text.strip()
    await update.message.reply_text(STEPS[3], parse_mode=ParseMode.MARKDOWN)
    return CBE


async def step_cbe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["cbe_account"] = update.message.text.strip()
    await update.message.reply_text(STEPS[4], parse_mode=ParseMode.MARKDOWN)
    return FRONT


async def step_front(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return FRONT
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["front_id"] = file.file_id
    await update.message.reply_text(STEPS[5], parse_mode=ParseMode.MARKDOWN)
    return BACK


async def step_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return BACK
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["back_id"] = file.file_id
    await update.message.reply_text(STEPS[6], parse_mode=ParseMode.MARKDOWN)
    return PHOTO


async def step_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Final step — save and forward to channel """
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return PHOTO

    uid = update.effective_user.id
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["personal_photo"] = file.file_id
    data = context.user_data["reg"]

    # ── Show completion to user ──
    await update.message.reply_text(
        done(data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu(),
    )

    # ── Forward to channel ──
    if CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=channel_msg(data, uid),
                parse_mode=ParseMode.MARKDOWN,
            )
            for key, cap in [
                ("front_id", "📷 Front ID | ፊት ጎን"),
                ("back_id", "📷 Back ID | ጀርባ ጎን"),
                ("personal_photo", "📷 Photo | ፎቶ"),
            ]:
                fid = data.get(key)
                if fid:
                    await context.bot.send_photo(chat_id=CHANNEL, photo=fid, caption=cap)

            log.info(f"✅ Registered | User={uid} | Name={data.get('first_name')}")
        except Exception as e:
            log.error(f"Channel error: {e}")

    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(CANCEL_MSG, parse_mode=ParseMode.MARKDOWN, reply_markup=menu())
    log.info(f"Cancelled | User={update.effective_user.id}")
    return ConversationHandler.END


# ══════════════════════════
# BUILD BOT
# ══════════════════════════

def build():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, btn_start)],
        states={
            FIRST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, step_first)],
            LAST:   [MessageHandler(filters.TEXT & ~filters.COMMAND, step_last)],
            MOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_mother)],
            CBE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, step_cbe)],
            FRONT:  [MessageHandler(filters.PHOTO, step_front)],
            BACK:   [MessageHandler(filters.PHOTO, step_back)],
            PHOTO:  [MessageHandler(filters.PHOTO, step_photo)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", cmd_start))

    return app


# ══════════════════════════
# RUN
# ══════════════════════════

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    log.info(f"Health server on port {PORT}")

    bot = build()
    log.info("✅ Bot running!")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)