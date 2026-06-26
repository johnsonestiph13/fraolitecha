#!/usr/bin/env python3
"""
Advanced Bilingual Telegram Registration Bot
Production-grade with error handling, retry logic, and health monitoring
"""

import os
import sys
import asyncio
import signal
import logging
import traceback
from datetime import datetime
from threading import Thread
from typing import Dict, Any, Optional

from flask import Flask
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackContext,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, NetworkError, TimedOut
from telegram.request import HTTPXRequest

# ============================
# LOGGING CONFIGURATION
# ============================
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ============================
# LOAD ENVIRONMENT
# ============================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
PORT = int(os.getenv("PORT", "10000"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Parse admin IDs with validation
try:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]
except ValueError:
    logger.error("❌ Invalid ADMIN_IDS format! Use comma-separated numbers.")
    ADMIN_IDS = []

# ============================
# VALIDATE REQUIRED ENV VARS
# ============================
if not TOKEN:
    logger.critical("❌ BOT_TOKEN is missing! Set it in environment variables.")
    sys.exit(1)

if not ADMIN_IDS:
    logger.warning("⚠️  No admin IDs configured. Admin commands will not work.")

logger.info(f"✅ Bot configured | Admins: {len(ADMIN_IDS)} | Channel: {ADMIN_CHANNEL_ID}")

# ============================
# FLASK HEALTH SERVER
# ============================
flask_app = Flask(__name__)
start_time = datetime.utcnow()

@flask_app.route("/")
def home():
    uptime = datetime.utcnow() - start_time
    return {
        "status": "healthy",
        "bot": "Bilingual Registration Bot",
        "uptime_seconds": int(uptime.total_seconds()),
        "stored_registrations": len(registry_map),
    }

@flask_app.route("/health")
def health():
    return {"status": "ok"}, 200

@flask_app.route("/stats")
def stats():
    pending = sum(1 for d in registry_map.values() if d["status"] == "PENDING")
    approved = sum(1 for d in registry_map.values() if d["status"] == "APPROVED")
    rejected = sum(1 for d in registry_map.values() if d["status"] == "REJECTED")
    return {
        "total": len(registry_map),
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
    }

# ============================
# IN-MEMORY STORAGE
# ============================
registry_map: Dict[int, Dict[str, Any]] = {}

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
START_BUTTON = "🚀 Start Service | አገልግሎት ጀምር"

# ============================
# BILINGUAL MESSAGE TEMPLATES
# ============================

WELCOME_MESSAGE = (
    "🌟 *Welcome!*\n"
    "🌟 *እንኳን ደህና መጡ!*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_We're glad to have you here._\n"
    "_በመምጣትዎ ደስተኞች ነን።_\n\n"
    "_Please follow the steps to complete your registration._\n"
    "_እባክዎ ምዝገባዎን ለማጠናቀቅ እርምጃዎቹን ይከተሉ።_"
)

FILL_INFO = (
    "📝 *Please fill the following information*\n"
    "📝 *እባክዎ የሚከተለውን መረጃ ይሙሉ*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_Let's begin! | እንጀምር!_"
)

FIRST_NAME_PROMPT = (
    "1️⃣ *First Name | የመጀመሪያ ስም*\n\n"
    "_Please enter your first name._\n"
    "_እባክዎ የመጀመሪያ ስምዎን ያስገቡ።_"
)

FATHERS_NAME_PROMPT = (
    "2️⃣ *Father's Name | የአባት ስም*\n\n"
    "_Please enter your father's name._\n"
    "_እባክዎ የአባትዎን ስም ያስገቡ።_"
)

MOTHERS_NAME_PROMPT = (
    "3️⃣ *Mother's Full Name | የእናት ሙሉ ስም*\n\n"
    "_Please enter your mother's full name._\n"
    "_እባክዎ የእናትዎን ሙሉ ስም ያስገቡ።_"
)

CBE_ACCOUNT_PROMPT = (
    "4️⃣ *CBE Account | ሲቢኢ አካውንት*\n\n"
    "_Please enter your CBE Account number._\n"
    "_እባክዎ የሲቢኢ አካውንት ቁጥርዎን ያስገቡ።_"
)

FRONT_ID_PROMPT = (
    "5️⃣ *Front ID | የመታወቂያ ፊት ጎን*\n\n"
    "📷 _Please upload a photo of the FRONT side of your ID._\n"
    "📷 _እባክዎ የመታወቂያዎን የፊት ጎን ፎቶ ያስገቡ።_"
)

BACK_ID_PROMPT = (
    "6️⃣ *Back ID | የመታወቂያ ጀርባ ጎን*\n\n"
    "📷 _Please upload a photo of the BACK side of your ID._\n"
    "📷 _እባክዎ የመታወቂያዎን የጀርባ ጎን ፎቶ ያስገቡ።_"
)

PHOTO_PROMPT = (
    "7️⃣ *Your Photo | የእርስዎ ፎቶ*\n\n"
    "📷 _Please upload your personal photo._\n"
    "📷 _እባክዎ የራስዎን ፎቶ ያስገቡ።_"
)

PHOTO_ERROR = (
    "❌ _Please upload a PHOTO, not a document._\n"
    "❌ _እባክዎ ሰነድ ሳይሆን ፎቶ ያስገቡ።_"
)

CANCEL_MESSAGE = (
    "❌ *Registration cancelled.*\n"
    "❌ *ምዝገባ ተሰርዟል።*\n\n"
    "_Press Start Service to begin again._\n"
    "_እንደገና ለመጀመር አገልግሎት ጀምር የሚለውን ይጫኑ።_"
)

# ============================
# MESSAGE BUILDERS
# ============================

def build_completion_message(user_data: Dict[str, str]) -> str:
    """Build the completion message with user data summary."""
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *You have finished all processes!*\n"
        "✅ *ሁሉንም ሂደቶች አጠናቀዋል!*\n\n"
        "*Please wait while we cross-check:*\n"
        "*እባክዎ እስክንፈትሽ ይጠብቁ:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | ስም:* {_safe(user_data, 'first_name')}\n"
        f"👤 *Father | አባት:* {_safe(user_data, 'fathers_name')}\n"
        f"👩 *Mother | እናት:* {_safe(user_data, 'mothers_name')}\n"
        f"🏦 *CBE Account | አካውንት:* {_safe(user_data, 'cbe_account')}\n\n"
        "📷 *Documents | ሰነዶች:*\n"
        "• Front ID | ፊት ጎን ✅\n"
        "• Back ID | ጀርባ ጎን ✅\n"
        "• Photo | ፎቶ ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ *_We will review your information shortly._*\n"
        "⏳ *_መረጃዎን በቅርቡ እንመረምራለን።_*"
    )

def build_admin_channel_message(user_id: int, user_data: Dict[str, str], status: str = "PENDING") -> str:
    """Build admin channel notification message."""
    return (
        "📋 *NEW REGISTRATION | አዲስ ምዝገባ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 *User ID:* `{user_id}`\n"
        f"📅 *Date:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | ስም:* {_safe(user_data, 'first_name')}\n"
        f"👤 *Father | አባት:* {_safe(user_data, 'fathers_name')}\n"
        f"👩 *Mother | እናት:* {_safe(user_data, 'mothers_name')}\n"
        f"🏦 *CBE | አካውንት:* {_safe(user_data, 'cbe_account')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ *Status | ሁኔታ:* {status}\n\n"
        "📷 *Documents Below | ሰነዶች ከዚህ በታች* 👇"
    )

def build_approval_message() -> str:
    return (
        "🎉 *Congratulations! | እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *Your registration has been APPROVED!*\n"
        "✅ *ምዝገባዎ ጸድቋል!*\n\n"
        "_Welcome aboard! | እንኳን ደህና መጡ!_"
    )

def build_rejection_message(reason: str = "") -> str:
    msg = (
        "⚠️ *Registration Update | የምዝገባ ማሻሻያ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "❌ *Your registration needs attention.*\n"
        "❌ *ምዝገባዎ እርማት ያስፈልገዋል።*\n\n"
    )
    if reason:
        msg += f"📝 *Reason | ምክንያት:* {reason}\n\n"
    msg += "_Please use /start to register again._\n_እባክዎ እንደገና /start ይጠቀሙ።_"
    return msg

# ============================
# UTILITY FUNCTIONS
# ============================

def _safe(data: Dict, key: str, default: str = "N/A") -> str:
    """Safely get value from dict with fallback."""
    value = data.get(key, default)
    return str(value) if value else default

def is_admin(user_id: int) -> bool:
    """Check if user is authorized admin."""
    return user_id in ADMIN_IDS

async def send_with_retry(bot, chat_id, text=None, photo=None, caption=None, parse_mode=None, max_retries=MAX_RETRIES):
    """Send message with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            if photo:
                return await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            else:
                return await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        except (NetworkError, TimedOut) as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(f"⚠️  Retry {attempt+1}/{max_retries} after {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                raise
        except Forbidden:
            logger.warning(f"🚫 User {chat_id} blocked the bot")
            raise
        except TelegramError as e:
            logger.error(f"❌ Telegram error: {e}")
            raise

def get_main_menu():
    """Create main menu keyboard."""
    keyboard = [[KeyboardButton(START_BUTTON)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ============================
# ERROR HANDLER
# ============================

async def error_handler(update: object, context: CallbackContext) -> None:
    """Global error handler for the bot."""
    logger.error(f"❌ Exception while handling update: {context.error}", exc_info=True)
    
    if isinstance(context.error, Forbidden):
        logger.warning("User blocked the bot — skipping")
        return
    
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Notify admins of critical errors
    if ADMIN_IDS and update and hasattr(update, 'effective_user'):
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ *Bot Error*\n```\n{tb_string[:1000]}\n```",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

# ============================
# USER HANDLERS
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"📥 /start | User: {user.id} | Name: {user.full_name}")
    
    context.user_data.clear()
    context.user_data["registration"] = {}
    
    try:
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"❌ Failed to send welcome: {e}")
    
    return ConversationHandler.END

async def start_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Start Service button."""
    if update.message.text != START_BUTTON:
        return ConversationHandler.END
    
    logger.info(f"🚀 Start Service | User: {update.effective_user.id}")
    
    await update.message.reply_text(
        FILL_INFO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(FIRST_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return FIRST_NAME

async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["first_name"] = update.message.text.strip()
    await update.message.reply_text(FATHERS_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return FATHERS_NAME

async def get_fathers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["fathers_name"] = update.message.text.strip()
    await update.message.reply_text(MOTHERS_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return MOTHERS_NAME

async def get_mothers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["mothers_name"] = update.message.text.strip()
    await update.message.reply_text(CBE_ACCOUNT_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return CBE_ACCOUNT

async def get_cbe_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["cbe_account"] = update.message.text.strip()
    await update.message.reply_text(FRONT_ID_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return FRONT_ID

async def get_front_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        context.user_data["registration"]["front_id"] = photo_file.file_id
        await update.message.reply_text(BACK_ID_PROMPT, parse_mode=ParseMode.MARKDOWN)
        return BACK_ID
    else:
        await update.message.reply_text(PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return FRONT_ID

async def get_back_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        context.user_data["registration"]["back_id"] = photo_file.file_id
        await update.message.reply_text(PHOTO_PROMPT, parse_mode=ParseMode.MARKDOWN)
        return PHOTO
    else:
        await update.message.reply_text(PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return BACK_ID

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step — save photo and complete registration."""
    if not update.message.photo:
        await update.message.reply_text(PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return PHOTO
    
    user_id = update.effective_user.id
    user_data = context.user_data["registration"]
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        user_data["personal_photo"] = photo_file.file_id
        
        # Send completion to user
        await update.message.reply_text(
            build_completion_message(user_data),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu()
        )
        
        # Forward to admin channel
        await _forward_to_admin(context, user_id, user_data)
        
        logger.info(f"✅ Registration complete | User: {user_id} | Name: {user_data.get('first_name')}")
        
    except Exception as e:
        logger.error(f"❌ Failed to complete registration for {user_id}: {e}")
        await update.message.reply_text(
            "❌ *Error! Please try again.*\n❌ *ስህተት! እባክዎ እንደገና ይሞክሩ።*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    return ConversationHandler.END

async def _forward_to_admin(context, user_id: int, user_data: Dict):
    """Forward registration data to admin channel."""
    if not ADMIN_CHANNEL_ID:
        logger.warning("⚠️  No admin channel configured — skipping forward")
        return
    
    try:
        # Send text summary
        admin_msg = await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=build_admin_channel_message(user_id, user_data, "⏳ PENDING"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send photos
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=user_data.get("front_id"),
            caption="📷 Front ID | የመታወቂያ ፊት ጎን"
        )
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=user_data.get("back_id"),
            caption="📷 Back ID | የመታወቂያ ጀርባ ጎን"
        )
        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=user_data.get("personal_photo"),
            caption="📷 Personal Photo | የግል ፎቶ"
        )
        
        # Store in memory
        registry_map[user_id] = {
            "channel_message_id": admin_msg.message_id,
            "status": "PENDING",
            "user_data": user_data,
            "registered_at": datetime.utcnow().isoformat(),
        }
        
    except Forbidden:
        logger.error(f"❌ Bot is not admin of channel {ADMIN_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"❌ Failed to forward to admin channel: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    logger.info(f"❌ Cancelled | User: {update.effective_user.id}")
    await update.message.reply_text(
        CANCEL_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

# ============================
# ADMIN COMMANDS
# ============================

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user registration: /approve [user_id]"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Usage: `/approve 123456789`\nአጠቃቀም: `/approve 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
        await context.bot.send_message(chat_id=target_id, text=build_approval_message(), parse_mode=ParseMode.MARKDOWN)
        
        if target_id in registry_map:
            registry_map[target_id]["status"] = "APPROVED"
        
        await update.message.reply_text(f"✅ Approved `{target_id}` | ጸድቋል")
        logger.info(f"✅ Admin {update.effective_user.id} approved user {target_id}")
        
    except Forbidden:
        await update.message.reply_text(f"❌ Cannot message user {target_id} (blocked)")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a user registration: /reject [user_id] [reason]"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 Usage: `/reject 123456789 reason`\nአጠቃቀም: `/reject 123456789 ምክንያት`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
        
        await context.bot.send_message(
            chat_id=target_id,
            text=build_rejection_message(reason),
            parse_mode=ParseMode.MARKDOWN
        )
        
        if target_id in registry_map:
            registry_map[target_id]["status"] = "REJECTED"
        
        await update.message.reply_text(f"❌ Rejected `{target_id}` | ውድቅ ተደርጓል")
        logger.info(f"❌ Admin rejected user {target_id}: {reason}")
        
    except Forbidden:
        await update.message.reply_text(f"❌ Cannot message user {target_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a user: /reply [user_id] [message]"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 Usage: `/reply 123456789 message`\nአጠቃቀም: `/reply 123456789 መልእክት`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
        message = " ".join(context.args[1:])
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"📬 *Admin Message | መልእክት*\n━━━━━━━━━━━━━━━\n\n{message}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await update.message.reply_text(f"✅ Sent to `{target_id}` | ተልኳል")
        logger.info(f"📬 Admin replied to {target_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List pending registrations: /pending"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    
    pending = {uid: d for uid, d in registry_map.items() if d["status"] == "PENDING"}
    
    if not pending:
        await update.message.reply_text("📋 No pending registrations | ምንም የለም")
        return
    
    msg = "📋 *Pending Registrations | በመጠባበቅ ላይ*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid, d in pending.items():
        ud = d["user_data"]
        msg += f"🔑 `{uid}`\n📝 {_safe(ud, 'first_name')} | 👤 {_safe(ud, 'fathers_name')}\n🏦 {_safe(ud, 'cbe_account')}\n───────────\n"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics: /stats"""
    if not is_admin(update.effective_user.id):
        return
    
    total = len(registry_map)
    pending = sum(1 for d in registry_map.values() if d["status"] == "PENDING")
    approved = sum(1 for d in registry_map.values() if d["status"] == "APPROVED")
    rejected = sum(1 for d in registry_map.values() if d["status"] == "REJECTED")
    
    msg = (
        "📊 *Bot Statistics | ስታቲስቲክስ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Total | ጠቅላላ: {total}\n"
        f"⏳ Pending | በመጠባበቅ: {pending}\n"
        f"✅ Approved | ጸድቋል: {approved}\n"
        f"❌ Rejected | ውድቅ: {rejected}\n"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ============================
# APPLICATION BUILDER
# ============================

def build_application() -> ApplicationBuilder:
    """Build and configure the bot application."""
    
    # HTTPX request with timeout and retry
    request = HTTPXRequest(
        connect_timeout=10.0,
        read_timeout=30.0,
        write_timeout=10.0,
        pool_timeout=5.0,
    )
    
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .request(request)
        .build()
    )
    
    # Conversation handler for registration flow
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, start_service)
        ],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            FATHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fathers_name)],
            MOTHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mothers_name)],
            CBE_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cbe_account)],
            FRONT_ID: [MessageHandler(filters.PHOTO, get_front_id)],
            BACK_ID: [MessageHandler(filters.PHOTO, get_back_id)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    
    # Register all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("reject", admin_reject))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(conv_handler)
    
    # Global error handler
    app.add_error_handler(error_handler)
    
    return app

# ============================
# MAIN ENTRY POINT
# ============================

async def run_bot():
    """Start the bot with graceful shutdown."""
    logger.info("=" * 50)
    logger.info("🤖 BOT INITIALIZING...")
    logger.info("=" * 50)
    
    app = build_application()
    
    logger.info("✅ All handlers registered")
    logger.info("🚀 Bot is now running...")
    logger.info("=" * 50)
    
    # Start polling with graceful stop on signals
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        close_loop=False,
        stop_signals=[signal.SIGINT, signal.SIGTERM],
    )

def run_health_server():
    """Run Flask health server in a separate thread."""
    try:
        flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")

# ============================
# STARTUP
# ============================

if __name__ == "__main__":
    logger.info("🌐 Starting health server on port %d", PORT)
    
    # Start Flask in daemon thread
    health_thread = Thread(target=run_health_server, daemon=True, name="health-server")
    health_thread.start()
    
    # Start bot (handles own event loop)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)