#!/usr/bin/env python3
"""
ULTIMATE TELEGRAM REGISTRATION BOT
Bilingual (English + አማርኛ) • Zero Conflicts • Perfect Flow
"""

import os
import sys
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

# ═══════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-6s │ %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("bot")

# ═══════════════════════════════════════════════
# ENVIRONMENT
# ═══════════════════════════════════════════════
load_dotenv()

TOKEN            = os.getenv("BOT_TOKEN", "")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID", "")
ADMIN_IDS_RAW    = os.getenv("ADMIN_IDS", "")
PORT             = int(os.getenv("PORT", "10000"))

ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

if not TOKEN:
    log.critical("❌ BOT_TOKEN is missing!")
    sys.exit(1)

log.info(f"✅ Boot | Admins={ADMIN_IDS} | Channel={ADMIN_CHANNEL_ID}")

# ═══════════════════════════════════════════════
# FLASK HEALTH SERVER
# ═══════════════════════════════════════════════
flask_app = Flask(__name__)
boot_time = datetime.now(timezone.utc)

@flask_app.route("/")
def home():
    uptime = str(datetime.now(timezone.utc) - boot_time)
    return f"🤖 Bot Online | Uptime: {uptime}"

@flask_app.route("/health")
def health():
    return "OK", 200

# ═══════════════════════════════════════════════
# IN-MEMORY REGISTRY
# ═══════════════════════════════════════════════
registry: Dict[int, Dict[str, Any]] = {}

# ═══════════════════════════════════════════════
# CONVERSATION STATES (7 steps)
# ═══════════════════════════════════════════════
(
    ST_FIRST_NAME,
    ST_FATHERS_NAME,
    ST_MOTHERS_NAME,
    ST_CBE_ACCOUNT,
    ST_FRONT_ID,
    ST_BACK_ID,
    ST_PHOTO,
) = range(7)

# ═══════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════
BTN_START = "🚀 Start Service | አገልግሎት ጀምር"

# ═══════════════════════════════════════════════
# MESSAGE TEMPLATES
# ═══════════════════════════════════════════════

WELCOME = (
    "🌟 *Welcome! | እንኳን ደህና መጡ!* 🌟\n\n"
    "_Complete your registration below._\n"
    "_እባክዎ ከታች ያለውን ምዝገባ ያጠናቅቁ።_"
)

BEGIN = "📝 *Let's begin! | እንጀምር!*"

ASK_FIRST   = "1️⃣ *First Name | የመጀመሪያ ስም*\n_Enter your first name:_"
ASK_FATHER  = "2️⃣ *Father's Name | የአባት ስም*\n_Enter your father's name:_"
ASK_MOTHER  = "3️⃣ *Mother's Full Name | የእናት ሙሉ ስም*\n_Enter your mother's full name:_"
ASK_CBE     = "4️⃣ *CBE Account | ሲቢኢ አካውንት*\n_Enter your CBE Account number:_"
ASK_FRONT   = "5️⃣ *Front ID | የመታወቂያ ፊት ጎን*\n📷 _Upload photo of FRONT of your ID:_"
ASK_BACK    = "6️⃣ *Back ID | የመታወቂያ ጀርባ ጎን*\n📷 _Upload photo of BACK of your ID:_"
ASK_PHOTO   = "7️⃣ *Your Photo | የእርስዎ ፎቶ*\n📷 _Upload your personal photo:_"
ERR_PHOTO   = "❌ *Please upload a PHOTO.*\n❌ *እባክዎ ፎቶ ያስገቡ።*"
CANCELLED   = "❌ *Cancelled | ተሰርዟል*\n_Press Start Service to try again._"

def DONE(data: Dict) -> str:
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *All steps complete! | ሁሉም ደረጃዎች ተጠናቀዋል!*\n\n"
        f"📋 *Name | ስም:* {G(data,'first_name')}\n"
        f"👤 *Father | አባት:* {G(data,'fathers_name')}\n"
        f"👩 *Mother | እናት:* {G(data,'mothers_name')}\n"
        f"🏦 *CBE | አካውንት:* {G(data,'cbe_account')}\n\n"
        "📷 *Documents | ሰነዶች:* ✅ All uploaded | ሁሉም ተልከዋል\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ *_We will review your information shortly._*\n"
        "⏳ *_መረጃዎን በቅርቡ እንመረምራለን።_*"
    )

def ADMIN_MSG(data: Dict, uid: int) -> str:
    return (
        "📋 *NEW REGISTRATION | አዲስ ምዝገባ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 *User ID:* `{uid}`\n"
        f"📅 *Date:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"📋 *Name | ስም:* {G(data,'first_name')}\n"
        f"👤 *Father | አባት:* {G(data,'fathers_name')}\n"
        f"👩 *Mother | እናት:* {G(data,'mothers_name')}\n"
        f"🏦 *CBE | አካውንት:* {G(data,'cbe_account')}\n\n"
        "⏳ *Status:* PENDING | በመጠባበቅ ላይ\n\n"
        "📷 *Documents Below | ሰነዶች ከዚህ በታች* 👇"
    )

APPROVED_MSG  = "🎉 *Approved! | ጸድቋል!* 🎉\n\n✅ _Your registration has been approved._\n✅ _ምዝገባዎ ጸድቋል።_"
REJECTED_MSG  = lambda r: f"⚠️ *Rejected | ውድቅ*\n\n📝 *Reason:* {r}\n\n_Please /start to re-register._"

# ═══════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════

def G(d: Dict, k: str, fb: str = "N/A") -> str:
    """Safe get from dict."""
    v = d.get(k, fb)
    return str(v).strip() if v else fb

def IS_ADMIN(uid: int) -> bool:
    return uid in ADMIN_IDS

def MAIN_MENU():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_START)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def CLEAR_MENU():
    return ReplyKeyboardRemove()

# ═══════════════════════════════════════════════
# ╔════════════════════════════════════════════╗
# ║         COMMAND HANDLERS (/)              ║
# ╚════════════════════════════════════════════╝
# ═══════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start — Entry point. Show welcome + button. """
    uid = update.effective_user.id
    log.info(f"▶ /start | User={uid}")

    # Wipe all previous data
    context.user_data.clear()

    await update.message.reply_text(
        WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU(),
    )
    # End any existing conversation
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /cancel — Abort registration. """
    uid = update.effective_user.id
    log.info(f"✖ /cancel | User={uid}")

    context.user_data.clear()

    await update.message.reply_text(
        CANCELLED,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU(),
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════
# ╔════════════════════════════════════════════╗
# ║       CONVERSATION STEP HANDLERS          ║
# ╚════════════════════════════════════════════╝
# ═══════════════════════════════════════════════

async def enter_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered ONLY by the Start Service button."""
    if update.message.text != BTN_START:
        return ConversationHandler.END  # Ignore other text

    uid = update.effective_user.id
    log.info(f"🚀 Start Service | User={uid}")

    # FRESH start for this user
    context.user_data.clear()
    context.user_data["reg"] = {}

    await update.message.reply_text(BEGIN, parse_mode=ParseMode.MARKDOWN, reply_markup=CLEAR_MENU())
    await update.message.reply_text(ASK_FIRST, parse_mode=ParseMode.MARKDOWN)

    return ST_FIRST_NAME


async def step_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["first_name"] = update.message.text.strip()
    await update.message.reply_text(ASK_FATHER, parse_mode=ParseMode.MARKDOWN)
    return ST_FATHERS_NAME


async def step_fathers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["fathers_name"] = update.message.text.strip()
    await update.message.reply_text(ASK_MOTHER, parse_mode=ParseMode.MARKDOWN)
    return ST_MOTHERS_NAME


async def step_mothers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["mothers_name"] = update.message.text.strip()
    await update.message.reply_text(ASK_CBE, parse_mode=ParseMode.MARKDOWN)
    return ST_CBE_ACCOUNT


async def step_cbe_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg"]["cbe_account"] = update.message.text.strip()
    await update.message.reply_text(ASK_FRONT, parse_mode=ParseMode.MARKDOWN)
    return ST_FRONT_ID


async def step_front_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return ST_FRONT_ID  # Wait until photo received

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["front_id"] = file.file_id
    await update.message.reply_text(ASK_BACK, parse_mode=ParseMode.MARKDOWN)
    return ST_BACK_ID


async def step_back_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return ST_BACK_ID

    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["back_id"] = file.file_id
    await update.message.reply_text(ASK_PHOTO, parse_mode=ParseMode.MARKDOWN)
    return ST_PHOTO


async def step_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step — complete registration."""
    if not update.message.photo:
        await update.message.reply_text(ERR_PHOTO, parse_mode=ParseMode.MARKDOWN)
        return ST_PHOTO

    uid  = update.effective_user.id
    file = await update.message.photo[-1].get_file()
    context.user_data["reg"]["personal_photo"] = file.file_id

    data = context.user_data["reg"]

    # ── Send completion to user ──
    await update.message.reply_text(
        DONE(data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU(),
    )

    # ── Forward to admin channel ──
    if ADMIN_CHANNEL_ID:
        try:
            # Text summary
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=ADMIN_MSG(data, uid),
                parse_mode=ParseMode.MARKDOWN,
            )
            # 3 Photos
            for key, caption in [
                ("front_id",        "📷 Front ID | የመታወቂያ ፊት ጎን"),
                ("back_id",         "📷 Back ID | የመታወቂያ ጀርባ ጎን"),
                ("personal_photo",  "📷 Personal Photo | የግል ፎቶ"),
            ]:
                fid = data.get(key)
                if fid:
                    await context.bot.send_photo(
                        chat_id=ADMIN_CHANNEL_ID,
                        photo=fid,
                        caption=caption,
                    )

            registry[uid] = {
                "status": "PENDING",
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            log.info(f"✅ Registered | User={uid} | Name={data.get('first_name')}")
        except Exception as e:
            log.error(f"❌ Channel send failed: {e}")

    return ConversationHandler.END


# ═══════════════════════════════════════════════
# ╔════════════════════════════════════════════╗
# ║           ADMIN COMMANDS (/)              ║
# ╚════════════════════════════════════════════╝
# ═══════════════════════════════════════════════

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /approve <user_id> """
    if not IS_ADMIN(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("📝 `/approve 123456789`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        uid = int(context.args[0])
        await context.bot.send_message(chat_id=uid, text=APPROVED_MSG, parse_mode=ParseMode.MARKDOWN)
        if uid in registry:
            registry[uid]["status"] = "APPROVED"
        await update.message.reply_text(f"✅ Approved `{uid}`")
        log.info(f"👑 Approved | Admin={update.effective_user.id} | User={uid}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /reject <user_id> <reason> """
    if not IS_ADMIN(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("📝 `/reject 123456789 blurry photo`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        uid    = int(context.args[0])
        reason = " ".join(context.args[1:]) or "No reason given"
        await context.bot.send_message(chat_id=uid, text=REJECTED_MSG(reason), parse_mode=ParseMode.MARKDOWN)
        if uid in registry:
            registry[uid]["status"] = "REJECTED"
        await update.message.reply_text(f"❌ Rejected `{uid}`")
        log.info(f"👑 Rejected | Admin={update.effective_user.id} | User={uid} | Reason={reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /reply <user_id> <message> """
    if not IS_ADMIN(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text("📝 `/reply 123456789 Hello!`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        uid = int(context.args[0])
        msg = " ".join(context.args[1:])
        await context.bot.send_message(
            chat_id=uid,
            text=f"📬 *Admin Message | ከአስተዳዳሪ መልእክት*\n━━━━━━━━━━━━━━━━━━\n\n{msg}",
            parse_mode=ParseMode.MARKDOWN,
        )
        await update.message.reply_text(f"✅ Sent to `{uid}`")
        log.info(f"👑 Reply | Admin={update.effective_user.id} | User={uid}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /pending — List all pending registrations. """
    if not IS_ADMIN(update.effective_user.id):
        return

    pending = {k: v for k, v in registry.items() if v["status"] == "PENDING"}

    if not pending:
        await update.message.reply_text("📋 No pending | ምንም የለም")
        return

    msg = "📋 *Pending Registrations | በመጠባበቅ ላይ*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid, d in pending.items():
        dd = d["data"]
        msg += (
            f"🔑 `{uid}`\n"
            f"📝 {G(dd,'first_name')} | 👤 {G(dd,'fathers_name')}\n"
            f"🏦 {G(dd,'cbe_account')}\n"
            f"───────────\n"
        )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /stats — Registration statistics. """
    if not IS_ADMIN(update.effective_user.id):
        return

    total    = len(registry)
    pending  = sum(1 for v in registry.values() if v["status"] == "PENDING")
    approved = sum(1 for v in registry.values() if v["status"] == "APPROVED")
    rejected = sum(1 for v in registry.values() if v["status"] == "REJECTED")

    msg = (
        "📊 *Statistics | ስታቲስቲክስ*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Total | ጠቅላላ: {total}\n"
        f"⏳ Pending | በመጠባበቅ: {pending}\n"
        f"✅ Approved | ጸድቋል: {approved}\n"
        f"❌ Rejected | ውድቅ: {rejected}\n"
    )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════
# ╔════════════════════════════════════════════╗
# ║         APPLICATION BUILDER               ║
# ╚════════════════════════════════════════════╝
# ═══════════════════════════════════════════════

def build_app():
    """Assemble the bot with perfect handler order."""

    app = ApplicationBuilder().token(TOKEN).build()

    # ── Conversation: Registration Flow ──
    reg_flow = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_conversation),
        ],
        states={
            ST_FIRST_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, step_first_name)],
            ST_FATHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_fathers_name)],
            ST_MOTHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_mothers_name)],
            ST_CBE_ACCOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, step_cbe_account)],
            ST_FRONT_ID:     [MessageHandler(filters.PHOTO, step_front_id)],
            ST_BACK_ID:      [MessageHandler(filters.PHOTO, step_back_id)],
            ST_PHOTO:        [MessageHandler(filters.PHOTO, step_photo)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
        per_message=False,
    )

    # ── REGISTER ORDER IS CRITICAL ──
    # 1. Conversation handler FIRST
    app.add_handler(reg_flow)

    # 2. User commands
    app.add_handler(CommandHandler("start", cmd_start))

    # 3. Admin commands
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("reject",  admin_reject))
    app.add_handler(CommandHandler("reply",   admin_reply))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("stats",   admin_stats))

    return app


# ═══════════════════════════════════════════════
# ╔════════════════════════════════════════════╗
# ║              MAIN ENTRY                   ║
# ╚════════════════════════════════════════════╝
# ═══════════════════════════════════════════════

def run_health_server():
    """Flask in background thread for Render health checks."""
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Start health server
    Thread(target=run_health_server, daemon=True, name="health").start()
    log.info(f"🌐 Health server on port {PORT}")

    # Build & run bot
    application = build_app()
    log.info("✅ All handlers registered")
    log.info("🚀 Bot is LIVE!")
    log.info("═" * 40)

    application.run_polling(allowed_updates=Update.ALL_TYPES)