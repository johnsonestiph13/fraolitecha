#!/usr/bin/env python3
"""
Telegram Registration Bot — Bilingual (English + አማርኛ)
Production-grade • Render-optimized • Python 3.12+
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from threading import Thread
from typing import Dict, Any

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

# ============================
# LOGGING
# ============================
logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger("bot")

# ============================
# ENVIRONMENT
# ============================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID", "")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
PORT = int(os.getenv("PORT", "10000"))

# Parse admin IDs
ADMIN_IDS = []
for aid in ADMIN_IDS_STR.split(","):
    aid = aid.strip()
    if aid.isdigit():
        ADMIN_IDS.append(int(aid))

if not TOKEN:
    logger.critical("BOT_TOKEN is missing!")
    sys.exit(1)

logger.info(f"Bot starting | Admins: {len(ADMIN_IDS)} | Channel: {ADMIN_CHANNEL_ID}")

# ============================
# FLASK HEALTH SERVER
# ============================
flask_app = Flask(__name__)
start_time = datetime.now(timezone.utc)

@flask_app.route("/")
def home():
    return {"status": "ok", "uptime": str(datetime.now(timezone.utc) - start_time)}

@flask_app.route("/health")
def health():
    return "OK", 200

# ============================
# STORAGE
# ============================
registry: Dict[int, Dict[str, Any]] = {}

# ============================
# CONVERSATION STATES
# ============================
(
    FIRST_NAME,
    FATHERS_NAME,
    MOTHERS_NAME,
    CBE_ACCOUNT,
    FRONT_ID,
    BACK_ID,
    PHOTO,
) = range(7)

# ============================
# CONSTANTS
# ============================
BTN_START_SERVICE = "🚀 Start Service | አገልግሎት ጀምር"

# ============================
# MESSAGES
# ============================

MSG_WELCOME = (
    "🌟 *Welcome! | እንኳን ደህና መጡ!* 🌟\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_We're glad to have you here._\n"
    "_በመምጣትዎ ደስተኞች ነን።_\n\n"
    "_Please follow the steps to complete your registration._\n"
    "_እባክዎ ምዝገባዎን ለማጠናቀቅ እርምጃዎቹን ይከተሉ።_"
)

MSG_FILL_INFO = (
    "📝 *Please fill the following information*\n"
    "📝 *እባክዎ የሚከተለውን መረጃ ይሙሉ*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_Let's begin! | እንጀምር!_"
)

MSG_FIRST_NAME = "1️⃣ *First Name | የመጀመሪያ ስም*\n\n_Please enter your first name._\n_እባክዎ የመጀመሪያ ስምዎን ያስገቡ።_"
MSG_FATHERS_NAME = "2️⃣ *Father's Name | የአባት ስም*\n\n_Please enter your father's name._\n_እባክዎ የአባትዎን ስም ያስገቡ።_"
MSG_MOTHERS_NAME = "3️⃣ *Mother's Full Name | የእናት ሙሉ ስም*\n\n_Please enter your mother's full name._\n_እባክዎ የእናትዎን ሙሉ ስም ያስገቡ።_"
MSG_CBE_ACCOUNT = "4️⃣ *CBE Account | ሲቢኢ አካውንት*\n\n_Please enter your CBE Account number._\n_እባክዎ የሲቢኢ አካውንት ቁጥርዎን ያስገቡ።_"
MSG_FRONT_ID = "5️⃣ *Front ID | የመታወቂያ ፊት ጎን*\n\n📷 _Please upload a photo of the FRONT side of your ID._\n📷 _እባክዎ የመታወቂያዎን የፊት ጎን ፎቶ ያስገቡ።_"
MSG_BACK_ID = "6️⃣ *Back ID | የመታወቂያ ጀርባ ጎን*\n\n📷 _Please upload a photo of the BACK side of your ID._\n📷 _እባክዎ የመታወቂያዎን የጀርባ ጎን ፎቶ ያስገቡ።_"
MSG_PHOTO = "7️⃣ *Your Photo | የእርስዎ ፎቶ*\n\n📷 _Please upload your personal photo._\n📷 _እባክዎ የራስዎን ፎቶ ያስገቡ።_"
MSG_PHOTO_ERROR = "❌ _Please upload a PHOTO, not a document._\n❌ _እባክዎ ሰነድ ሳይሆን ፎቶ ያስገቡ።_"
MSG_CANCEL = (
    "❌ *Registration cancelled.*\n"
    "❌ *ምዝገባ ተሰርዟል።*\n\n"
    "_Press Start Service to begin again._\n"
    "_እንደገና ለመጀመር አገልግሎት ጀምር የሚለውን ይጫኑ።_"
)

# ============================
# MESSAGE BUILDERS
# ============================

def _s(d: Dict, k: str, fallback: str = "N/A") -> str:
    """Safely get string from dict."""
    v = d.get(k, fallback)
    return str(v) if v else fallback

def msg_completion(data: Dict) -> str:
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *You have finished all processes!*\n"
        "✅ *ሁሉንም ሂደቶች አጠናቀዋል!*\n\n"
        "*Please wait while we cross-check:*\n"
        "*እባክዎ እስክንፈትሽ ይጠብቁ:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | ስም:* {_s(data, 'first_name')}\n"
        f"👤 *Father | አባት:* {_s(data, 'fathers_name')}\n"
        f"👩 *Mother | እናት:* {_s(data, 'mothers_name')}\n"
        f"🏦 *CBE Account | አካውንት:* {_s(data, 'cbe_account')}\n\n"
        "📷 *Documents | ሰነዶች:*\n"
        "• Front ID | ፊት ጎን ✅\n"
        "• Back ID | ጀርባ ጎን ✅\n"
        "• Photo | ፎቶ ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ *_We will review your information shortly._*\n"
        "⏳ *_መረጃዎን በቅርቡ እንመረምራለን።_*"
    )

def msg_admin(data: Dict, uid: int, status: str = "⏳ PENDING") -> str:
    return (
        "📋 *NEW REGISTRATION | አዲስ ምዝገባ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 *User ID:* `{uid}`\n"
        f"📅 *Date:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"📋 *First Name | ስም:* {_s(data, 'first_name')}\n"
        f"👤 *Father | አባት:* {_s(data, 'fathers_name')}\n"
        f"👩 *Mother | እናት:* {_s(data, 'mothers_name')}\n"
        f"🏦 *CBE | አካውንት:* {_s(data, 'cbe_account')}\n\n"
        f"*Status | ሁኔታ:* {status}\n\n"
        "📷 *Documents Below | ሰነዶች ከዚህ በታች* 👇"
    )

def msg_approved() -> str:
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *Your registration has been APPROVED!*\n"
        "✅ *ምዝገባዎ ጸድቋል!*\n\n"
        "_Welcome aboard! | እንኳን ደህና መጡ!_"
    )

def msg_rejected(reason: str = "") -> str:
    m = (
        "⚠️ *Registration Update | የምዝገባ ማሻሻያ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "❌ *Your registration needs attention.*\n"
        "❌ *ምዝገባዎ እርማት ያስፈልገዋል።*\n\n"
    )
    if reason:
        m += f"📝 *Reason | ምክንያት:* {reason}\n\n"
    m += "_Please use /start to register again._\n_እባክዎ እንደገና /start ይጠቀሙ።_"
    return m

# ============================
# KEYBOARD
# ============================

def main_menu():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_START_SERVICE)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def remove_menu():
    return ReplyKeyboardRemove()

# ============================
# HELPERS
# ============================

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

async def send_photos_to_channel(bot, chat_id: str, data: Dict):
    """Send 3 photos to admin channel."""
    for key, caption in [
        ("front_id", "📷 Front ID | የመታወቂያ ፊት ጎን"),
        ("back_id", "📷 Back ID | የመታወቂያ ጀርባ ጎን"),
        ("personal_photo", "📷 Personal Photo | የግል ፎቶ"),
    ]:
        file_id = data.get(key)
        if file_id:
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)

# ============================
# HANDLERS
# ============================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — show welcome with button."""
    uid = update.effective_user.id
    logger.info(f"/start | User: {uid} | {update.effective_user.full_name}")

    # Clear any stale conversation data
    context.user_data.clear()
    context.user_data["reg"] = {}

    await update.message.reply_text(
        MSG_WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(),
    )
    # Return END so we don't stay in any conversation
    return ConversationHandler.END


async def btn_start_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked 'Start Service' button — begin registration."""
    uid = update.effective_user.id

    # Only trigger on exact button text
    if update.message.text != BTN_START_SERVICE:
        return ConversationHandler.END

    logger.info(f"Start Service | User: {uid}")

    # Clear any stale data
    context.user_data.clear()
    context.user_data["reg"] = {}

    # Remove button, show info
    await update.message.reply_text(MSG_FILL_INFO, parse_mode=ParseMode.MARKDOWN, reply_markup=remove_menu())
    await update.message.reply_text(MSG_FIRST_NAME, parse_mode=ParseMode.MARKDOWN)

    return FIRST_NAME


async def step_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["first_name"] = update.message.text.strip()
    await update.message.reply_text(MSG_FATHERS_NAME, parse_mode=ParseMode.MARKDOWN)
    return FATHERS_NAME


async def step_fathers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["fathers_name"] = update.message.text.strip()
    await update.message.reply_text(MSG_MOTHERS_NAME, parse_mode=ParseMode.MARKDOWN)
    return MOTHERS_NAME


async def step_mothers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["mothers_name"] = update.message.text.strip()
    await update.message.reply_text(MSG_CBE_ACCOUNT, parse_mode=ParseMode.MARKDOWN)
    return CBE_ACCOUNT


async def step_cbe_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["cbe_account"] = update.message.text.strip()
    await update.message.reply_text(MSG_FRONT_ID, parse_mode=ParseMode.MARKDOWN)
    return FRONT_ID


async def step_front_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(MSG_PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return FRONT_ID  # Stay in same state

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["front_id"] = file.file_id
    await update.message.reply_text(MSG_BACK_ID, parse_mode=ParseMode.MARKDOWN)
    return BACK_ID


async def step_back_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(MSG_PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return BACK_ID  # Stay in same state

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["back_id"] = file.file_id
    await update.message.reply_text(MSG_PHOTO, parse_mode=ParseMode.MARKDOWN)
    return PHOTO


async def step_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step — save photo and complete."""
    if not update.message.photo:
        await update.message.reply_text(MSG_PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return PHOTO  # Stay in same state

    uid = update.effective_user.id
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["personal_photo"] = file.file_id

    data = context.user_data["reg"]

    # Show completion to user
    await update.message.reply_text(
        msg_completion(data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(),
    )

    # Forward to admin channel
    if ADMIN_CHANNEL_ID:
        try:
            # Send text summary
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=msg_admin(data, uid),
                parse_mode=ParseMode.MARKDOWN,
            )
            # Send photos
            await send_photos_to_channel(context.bot, ADMIN_CHANNEL_ID, data)

            # Store in memory
            registry[uid] = {
                "status": "PENDING",
                "data": data,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"Registration complete | User: {uid} | {data.get('first_name')}")
        except Exception as e:
            logger.error(f"Failed to forward to channel: {e}")

    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration."""
    uid = update.effective_user.id
    logger.info(f"Cancelled | User: {uid}")
    await update.message.reply_text(
        MSG_CANCEL,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


# ============================
# ADMIN COMMANDS
# ============================

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /approve <user_id> """
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/approve 123456789`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        target = int(context.args[0])
        await context.bot.send_message(chat_id=target, text=msg_approved(), parse_mode=ParseMode.MARKDOWN)

        if target in registry:
            registry[target]["status"] = "APPROVED"

        await update.message.reply_text(f"✅ Approved `{target}`")
        logger.info(f"Admin approved user {target}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        logger.error(f"Approve error: {e}")


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /reject <user_id> <reason> """
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/reject 123456789 reason`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        target = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        await context.bot.send_message(chat_id=target, text=msg_rejected(reason), parse_mode=ParseMode.MARKDOWN)

        if target in registry:
            registry[target]["status"] = "REJECTED"

        await update.message.reply_text(f"❌ Rejected `{target}`")
        logger.info(f"Admin rejected user {target}: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /reply <user_id> <message> """
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/reply 123456789 message`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        target = int(context.args[0])
        message = " ".join(context.args[1:])

        await context.bot.send_message(
            chat_id=target,
            text=f"📬 *Admin Message | መልእክት*\n━━━━━━━━━━━━━━━\n\n{message}",
            parse_mode=ParseMode.MARKDOWN,
        )

        await update.message.reply_text(f"✅ Sent to `{target}`")
        logger.info(f"Admin replied to {target}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /pending — list pending registrations """
    if not is_admin(update.effective_user.id):
        return

    pending = {uid: d for uid, d in registry.items() if d["status"] == "PENDING"}

    if not pending:
        await update.message.reply_text("📋 No pending registrations | ምንም የለም")
        return

    msg = "📋 *Pending | በመጠባበቅ ላይ*\n━━━━━━━━━━━━━━━━\n\n"
    for uid, d in pending.items():
        dd = d["data"]
        msg += (
            f"🔑 `{uid}`\n"
            f"📝 {_s(dd, 'first_name')} | 👤 {_s(dd, 'fathers_name')}\n"
            f"🏦 {_s(dd, 'cbe_account')}\n"
            f"───────────\n"
        )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /stats — show statistics """
    if not is_admin(update.effective_user.id):
        return

    total = len(registry)
    pending = sum(1 for d in registry.values() if d["status"] == "PENDING")
    approved = sum(1 for d in registry.values() if d["status"] == "APPROVED")
    rejected = sum(1 for d in registry.values() if d["status"] == "REJECTED")

    msg = (
        "📊 *Statistics | ስታቲስቲክስ*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📋 Total | ጠቅላላ: {total}\n"
        f"⏳ Pending | በመጠባበቅ: {pending}\n"
        f"✅ Approved | ጸድቋል: {approved}\n"
        f"❌ Rejected | ውድቅ: {rejected}\n"
    )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ============================
# BUILD APPLICATION
# ============================

def build_app():
    """Build and return configured Application."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Registration conversation
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, btn_start_service),
        ],
        states={
            FIRST_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, step_first_name)],
            FATHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_fathers_name)],
            MOTHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_mothers_name)],
            CBE_ACCOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, step_cbe_account)],
            FRONT_ID:     [MessageHandler(filters.PHOTO, step_front_id)],
            BACK_ID:      [MessageHandler(filters.PHOTO, step_back_id)],
            PHOTO:        [MessageHandler(filters.PHOTO, step_photo)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
        per_message=False,
    )

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("reject", admin_reject))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(conv)

    return app


# ============================
# FLASK SERVER
# ============================

def run_health_server():
    """Run Flask in background thread."""
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


# ============================
# MAIN
# ============================

if __name__ == "__main__":
    # Start health server in background
    Thread(target=run_health_server, daemon=True, name="health").start()
    logger.info(f"Health server on port {PORT}")

    # Build and run bot
    application = build_app()
    logger.info("✅ All handlers registered")
    logger.info("🚀 Bot is running...")
    logger.info("=" * 40)

    application.run_polling(allowed_updates=Update.ALL_TYPES)