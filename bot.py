#!/usr/bin/env python3
"""
Telegram Registration Bot — Button-by-Button + Auto-Forward
Bilingual (English + አማርኛ) • 7 Button Steps • All Messages to Channel
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
# BUTTON LABELS
# ══════════════════════════
BTN_START   = "🚀 Start Service | አገልግሎት ጀምር"
BTN_FIRST   = "1️⃣ First Name | የመጀመሪያ ስም"
BTN_LAST    = "2️⃣ Last Name | የአያት ስም"
BTN_MOTHER  = "3️⃣ Mother's Name | የእናት ስም"
BTN_CBE     = "4️⃣ CBE Account | ሲቢኢ አካውንት"
BTN_FRONT   = "5️⃣ Front ID | የመታወቂያ ፊት ጎን"
BTN_BACK    = "6️⃣ Back ID | የመታወቂያ ጀርባ ጎን"
BTN_PHOTO   = "7️⃣ Your Photo | የእርስዎ ፎቶ"
BTN_DONE    = "✅ Submit | አስገባ"
BTN_CANCEL  = "❌ Cancel | ሰርዝ"

# ══════════════════════════
# KEYBOARDS
# ══════════════════════════

def menu_start():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_START)]], resize_keyboard=True)

def menu_first():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_FIRST)]], resize_keyboard=True)

def menu_last():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_LAST)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_mother():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_MOTHER)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_cbe():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CBE)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_front():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_FRONT)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_back():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_photo():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_PHOTO)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def menu_done():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_DONE)], [KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def hide():
    return ReplyKeyboardRemove()

# ══════════════════════════
# MESSAGES
# ══════════════════════════

WELCOME = (
    "🌟 *Welcome! | እንኳን ደህና መጡ!* 🌟\n\n"
    "_Please click the button below to start._\n"
    "_እባክዎ ከታች ያለውን ቁልፍ ይጫኑ።_"
)

PROMPT_FIRST  = "📝 *Please type your first name below:*\n📝 *እባክዎ ስምዎን ከታች ይጻፉ:*"
PROMPT_LAST   = "📝 *Please type your last name below:*\n📝 *እባክዎ የአያት ስምዎን ከታች ይጻፉ:*"
PROMPT_MOTHER = "📝 *Please type your mother's full name below:*\n📝 *እባክዎ የእናትዎን ሙሉ ስም ከታች ይጻፉ:*"
PROMPT_CBE    = "📝 *Please type your CBE Account number below:*\n📝 *እባክዎ የሲቢኢ አካውንት ቁጥርዎን ከታች ይጻፉ:*"
PROMPT_FRONT  = "📷 *Please upload photo of FRONT of your ID:*\n📷 *እባክዎ የመታወቂያዎን የፊት ጎን ፎቶ ይላኩ:*"
PROMPT_BACK   = "📷 *Please upload photo of BACK of your ID:*\n📷 *እባክዎ የመታወቂያዎን የጀርባ ጎን ፎቶ ይላኩ:*"
PROMPT_PHOTO  = "📷 *Please upload your personal photo:*\n📷 *እባክዎ የራስዎን ፎቶ ይላኩ:*"

ERR_PHOTO = "❌ *Please upload a PHOTO.*\n❌ *እባክዎ ፎቶ ይላኩ።*"

CANCEL_MSG = "❌ *Cancelled | ተሰርዟል*\n\n_Press Start Service to try again._\n_እንደገና ለመሞከር አገልግሎት ጀምር ይጫኑ።_"

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
        f"🏦 *CBE | አካውንት:* {data.get('cbe_account','')}\n\n"
        "📷 *Documents | ሰነዶች:*\n"
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
# FORWARD TO CHANNEL
# ══════════════════════════

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward EVERY message from user to admin channel."""
    if not CHANNEL or not update.message:
        return

    user = update.effective_user
    uid = user.id
    name = user.full_name
    username = f"@{user.username}" if user.username else "No username"

    try:
        # Forward text messages
        if update.message.text:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"📩 *New Message | አዲስ መልእክት*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 *From:* {name}\n"
                    f"🔑 *ID:* `{uid}`\n"
                    f"📎 *Username:* {username}\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"{update.message.text}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        # Forward photos
        elif update.message.photo:
            caption = update.message.caption or ""
            await context.bot.send_photo(
                chat_id=CHANNEL,
                photo=update.message.photo[-1].file_id,
                caption=(
                    f"📷 *Photo from:* {name}\n"
                    f"🔑 *ID:* `{uid}`\n"
                    f"📎 *Username:* {username}\n"
                    f"{'📝 ' + caption if caption else ''}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        # Forward documents
        elif update.message.document:
            await context.bot.send_document(
                chat_id=CHANNEL,
                document=update.message.document.file_id,
                caption=(
                    f"📄 *Document from:* {name}\n"
                    f"🔑 *ID:* `{uid}`\n"
                    f"📎 *Username:* {username}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        # Forward stickers
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=CHANNEL,
                sticker=update.message.sticker.file_id,
            )
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=f"🎯 *Sticker from:* {name} | `{uid}`",
                parse_mode=ParseMode.MARKDOWN,
            )

        # Forward any other message type
        else:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"📩 *Other message from:* {name}\n"
                    f"🔑 *ID:* `{uid}`\n"
                    f"📎 *Username:* {username}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as e:
        log.error(f"Forward error: {e}")


# ══════════════════════════
# HANDLERS
# ══════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_start())
    log.info(f"/start | User={update.effective_user.id}")


async def btn_start_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != BTN_START:
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["reg"] = {}

    await update.message.reply_text(
        "👇 *Click the button below to enter your First Name:*\n👇 *ስምዎን ለማስገባት ከታች ያለውን ቁልፍ ይጫኑ:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_first(),
    )
    log.info(f"Start | User={update.effective_user.id}")
    return FIRST


async def btn_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != BTN_FIRST:
        return FIRST
    await update.message.reply_text(PROMPT_FIRST, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
    return FIRST


async def get_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["first_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *Saved:* {update.message.text.strip()}\n\n👇 *Click below for Last Name:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_last(),
    )
    return LAST


async def btn_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_LAST:
        await update.message.reply_text(PROMPT_LAST, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return LAST
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return LAST


async def get_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["last_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *Saved:* {update.message.text.strip()}\n\n👇 *Click below for Mother's Name:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_mother(),
    )
    return MOTHER


async def btn_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_MOTHER:
        await update.message.reply_text(PROMPT_MOTHER, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return MOTHER
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return MOTHER


async def get_mother(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["mothers_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *Saved:* {update.message.text.strip()}\n\n👇 *Click below for CBE Account:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_cbe(),
    )
    return CBE


async def btn_cbe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_CBE:
        await update.message.reply_text(PROMPT_CBE, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return CBE
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return CBE


async def get_cbe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["cbe_account"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *Saved:* {update.message.text.strip()}\n\n👇 *Click below to upload Front ID:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_front(),
    )
    return FRONT


async def btn_front(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_FRONT:
        await update.message.reply_text(PROMPT_FRONT, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return FRONT
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return FRONT


async def get_front(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return FRONT
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["front_id"] = file.file_id
    await update.message.reply_text(
        "✅ *Photo saved!*\n\n👇 *Click below to upload Back ID:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_back(),
    )
    return BACK


async def btn_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_BACK:
        await update.message.reply_text(PROMPT_BACK, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return BACK
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return BACK


async def get_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return BACK
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["back_id"] = file.file_id
    await update.message.reply_text(
        "✅ *Photo saved!*\n\n👇 *Click below to upload your photo:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_photo(),
    )
    return PHOTO


async def btn_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_PHOTO:
        await update.message.reply_text(PROMPT_PHOTO, parse_mode=ParseMode.MARKDOWN, reply_markup=hide())
        return PHOTO
    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return PHOTO
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["personal_photo"] = file.file_id
    await update.message.reply_text(
        "✅ *Photo saved!*\n\n👇 *Click SUBMIT to finish:*\n👇 *ለመጨረስ አስገባ የሚለውን ይጫኑ:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_done(),
    )
    return PHOTO


async def submit_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BTN_DONE:
        uid = update.effective_user.id
        data = context.user_data["reg"]

        await update.message.reply_text(
            done(data),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_start(),
        )

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

                log.info(f"✅ Registered | User={uid} | {data.get('first_name')}")
            except Exception as e:
                log.error(f"Channel error: {e}")

        return ConversationHandler.END

    elif update.message.text == BTN_CANCEL:
        return await do_cancel(update, context)

    return PHOTO


async def do_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(CANCEL_MSG, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_start())
    log.info(f"Cancelled | User={update.effective_user.id}")
    return ConversationHandler.END


# ══════════════════════════
# BUILD BOT
# ══════════════════════════

def build():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, btn_start_service),
        ],
        states={
            FIRST: [
                MessageHandler(filters.Regex(f"^{BTN_FIRST}$"), btn_first),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_first),
            ],
            LAST: [
                MessageHandler(filters.Regex(f"^{BTN_LAST}$"), btn_last),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_last),
            ],
            MOTHER: [
                MessageHandler(filters.Regex(f"^{BTN_MOTHER}$"), btn_mother),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_mother),
            ],
            CBE: [
                MessageHandler(filters.Regex(f"^{BTN_CBE}$"), btn_cbe),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_cbe),
            ],
            FRONT: [
                MessageHandler(filters.Regex(f"^{BTN_FRONT}$"), btn_front),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.PHOTO, get_front),
            ],
            BACK: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), btn_back),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.PHOTO, get_back),
            ],
            PHOTO: [
                MessageHandler(filters.Regex(f"^{BTN_PHOTO}$"), btn_photo),
                MessageHandler(filters.Regex(f"^{BTN_DONE}$"), submit_final),
                MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), do_cancel),
                MessageHandler(filters.PHOTO, get_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", do_cancel)],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", cmd_start))

    # ⭐ AUTO-FORWARD: Catch ALL messages and forward to channel
    app.add_handler(
        MessageHandler(filters.ALL, forward_to_channel),
        group=999,  # Lowest priority — runs AFTER all other handlers
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
    log.info("✅ Bot running with auto-forward!")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)