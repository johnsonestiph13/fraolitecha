import os
import asyncio
from threading import Thread
from flask import Flask, request, Response
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ============================
# LOAD ENV
# ============================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")

# ============================
# FLASK APP (to keep Render happy)
# ============================
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 Bot is running! | ቦቱ እየሰራ ነው!"

@flask_app.route("/health")
def health():
    return "OK", 200

# ============================
# IN-MEMORY STORAGE
# ============================
registry_map = {}

# ============================
# STATES
# ============================
FIRST_NAME, FATHERS_NAME, MOTHERS_NAME, CBE_ACCOUNT, FRONT_ID, BACK_ID, PHOTO = range(7)

# ============================
# BILINGUAL MESSAGES
# ============================
WELCOME_MESSAGE = (
    "🌟 *Welcome!*                    |                    *እንኳን ደህና መጡ!* 🌟\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_We're glad to have you here._\n"
    "_በመምጣትዎ ደስተኞች ነን።_\n\n"
    "_Please follow the steps to complete your registration._\n"
    "_እባክዎ ምዝገባዎን ለማጠናቀቅ እርምጃዎቹን ይከተሉ።_"
)

START_BUTTON = "🚀 Start Service | አገልግሎት ጀምር"

FILL_INFO = (
    "📝 *Please fill the following information*\n"
    "📝 *እባክዎ የሚከተለውን መረጃ ይሙሉ*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "_Let's begin! | እንጀምር!_"
)

FIRST_NAME_PROMPT = (
    "1️⃣ *First Name:*\n"
    "1️⃣ *የመጀመሪያ ስም:*\n\n"
    "_Please enter your first name._\n"
    "_እባክዎ የመጀመሪያ ስምዎን ያስገቡ።_"
)

FATHERS_NAME_PROMPT = (
    "2️⃣ *Father's Name:*\n"
    "2️⃣ *የአባት ስም:*\n\n"
    "_Please enter your father's name._\n"
    "_እባክዎ የአባትዎን ስም ያስገቡ።_"
)

MOTHERS_NAME_PROMPT = (
    "3️⃣ *Mother's Full Name:*\n"
    "3️⃣ *የእናት ሙሉ ስም:*\n\n"
    "_Please enter your mother's full name._\n"
    "_እባክዎ የእናትዎን ሙሉ ስም ያስገቡ።_"
)

CBE_ACCOUNT_PROMPT = (
    "4️⃣ *CBE Account:*\n"
    "4️⃣ *ሲቢኢ አካውንት:*\n\n"
    "_Please enter your CBE Account number._\n"
    "_እባክዎ የሲቢኢ አካውንት ቁጥርዎን ያስገቡ።_"
)

FRONT_ID_PROMPT = (
    "5️⃣ *Front ID:*\n"
    "5️⃣ *የመታወቂያ ፊት ጎን:*\n\n"
    "📷 _Please upload a photo of the FRONT side of your ID._\n"
    "📷 _እባክዎ የመታወቂያዎን የፊት ጎን ፎቶ ያስገቡ።_"
)

BACK_ID_PROMPT = (
    "6️⃣ *Back ID:*\n"
    "6️⃣ *የመታወቂያ ጀርባ ጎን:*\n\n"
    "📷 _Please upload a photo of the BACK side of your ID._\n"
    "📷 _እባክዎ የመታወቂያዎን የጀርባ ጎን ፎቶ ያስገቡ።_"
)

PHOTO_PROMPT = (
    "7️⃣ *Your Photo:*\n"
    "7️⃣ *የእርስዎ ፎቶ:*\n\n"
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

def get_completion_message(user_data):
    return (
        "🎉 *Congratulations!*                    |                    *እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *You have finished all processes!*\n"
        "✅ *ሁሉንም ሂደቶች አጠናቀዋል!*\n\n"
        "*Please wait while we cross-check the information you entered:*\n"
        "*እባክዎ ያስገቡትን መረጃ እስክንፈትሽ ይጠብቁ:*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | የመጀመሪያ ስም:* {user_data.get('first_name')}\n"
        f"👤 *Father's Name | የአባት ስም:* {user_data.get('fathers_name')}\n"
        f"👩 *Mother's Full Name | የእናት ሙሉ ስም:* {user_data.get('mothers_name')}\n"
        f"🏦 *CBE Account | ሲቢኢ አካውንት:* {user_data.get('cbe_account')}\n\n"
        "📷 *Documents Uploaded | የተላኩ ሰነዶች:*\n"
        "• Front ID | የመታወቂያ ፊት ጎን ✅\n"
        "• Back ID | የመታወቂያ ጀርባ ጎን ✅\n"
        "• Personal Photo | የግል ፎቶ ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ *_We will review your information shortly._*\n"
        "⏳ *_መረጃዎን በቅርቡ እንመረምራለን።_*"
    )

def get_admin_channel_message(user_id, user_data, status="PENDING"):
    return (
        "📋 *NEW REGISTRATION*                |                *አዲስ ምዝገባ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 *User ID | የተጠቃሚ መታወቂያ:* `{user_id}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *First Name | የመጀመሪያ ስም:* {user_data.get('first_name')}\n"
        f"👤 *Father's Name | የአባት ስም:* {user_data.get('fathers_name')}\n"
        f"👩 *Mother's Full Name | የእናት ሙሉ ስም:* {user_data.get('mothers_name')}\n"
        f"🏦 *CBE Account | ሲቢኢ አካውንት:* {user_data.get('cbe_account')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ *Status | ሁኔታ:* {status}\n\n"
        "📷 *Documents Below | ሰነዶች ከዚህ በታች* 👇"
    )

def get_approval_message():
    return (
        "🎉 *Congratulations!*                    |                    *እንኳን ደስ አለዎት!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *Your registration has been APPROVED!*\n"
        "✅ *ምዝገባዎ ጸድቋል!*\n\n"
        "_Welcome aboard! | እንኳን ደህና መጡ!_"
    )

def get_rejection_message(reason=""):
    msg = (
        "⚠️ *Registration Update*                |                *የምዝገባ ማሻሻያ*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "❌ *Your registration needs attention.*\n"
        "❌ *ምዝገባዎ እርማት ያስፈልገዋል።*\n\n"
    )
    if reason:
        msg += f"📝 *Reason | ምክንያት:* {reason}\n\n"
    msg += (
        "_Please use /start to register again._\n"
        "_እባክዎ እንደገና ለመመዝገብ /start ይጠቀሙ።_"
    )
    return msg

# ============================
# KEYBOARD
# ============================
def get_main_menu():
    keyboard = [[KeyboardButton(START_BUTTON)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ============================
# HELPER
# ============================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================
# HANDLERS
# ============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["registration"] = {}
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )
    print(f"✅ /start from user {update.effective_user.id}")
    return ConversationHandler.END

async def start_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if it's the button text
    if update.message.text != START_BUTTON:
        return ConversationHandler.END
    
    await update.message.reply_text(FILL_INFO, parse_mode=ParseMode.MARKDOWN, reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(FIRST_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return FIRST_NAME

async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["first_name"] = update.message.text
    await update.message.reply_text(FATHERS_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return FATHERS_NAME

async def get_fathers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["fathers_name"] = update.message.text
    await update.message.reply_text(MOTHERS_NAME_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return MOTHERS_NAME

async def get_mothers_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["mothers_name"] = update.message.text
    await update.message.reply_text(CBE_ACCOUNT_PROMPT, parse_mode=ParseMode.MARKDOWN)
    return CBE_ACCOUNT

async def get_cbe_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["registration"]["cbe_account"] = update.message.text
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
    if not update.message.photo:
        await update.message.reply_text(PHOTO_ERROR, parse_mode=ParseMode.MARKDOWN)
        return PHOTO
    
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    context.user_data["registration"]["personal_photo"] = photo_file.file_id
    user_data = context.user_data["registration"]
    
    await update.message.reply_text(
        get_completion_message(user_data),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )
    
    # Forward to Admin Channel
    if ADMIN_CHANNEL_ID:
        try:
            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=get_admin_channel_message(user_id, user_data, "⏳ PENDING | በመጠባበቅ ላይ"),
                parse_mode=ParseMode.MARKDOWN
            )
            await context.bot.send_photo(
                chat_id=ADMIN_CHANNEL_ID,
                photo=user_data["front_id"],
                caption="📷 Front ID | የመታወቂያ ፊት ጎን"
            )
            await context.bot.send_photo(
                chat_id=ADMIN_CHANNEL_ID,
                photo=user_data["back_id"],
                caption="📷 Back ID | የመታወቂያ ጀርባ ጎን"
            )
            await context.bot.send_photo(
                chat_id=ADMIN_CHANNEL_ID,
                photo=user_data["personal_photo"],
                caption="📷 Personal Photo | የግል ፎቶ"
            )
            registry_map[user_id] = {
                "channel_message_id": admin_msg.message_id,
                "status": "PENDING",
                "user_data": user_data
            }
            print(f"✅ Registration forwarded to admin channel for user {user_id}")
        except Exception as e:
            print(f"❌ Error sending to admin channel: {e}")
    
    print(f"✅ Registration complete for user {user_id}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        CANCEL_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )
    print(f"❌ Registration cancelled by user {update.effective_user.id}")
    return ConversationHandler.END

# ============================
# ADMIN COMMANDS
# ============================
async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/approve 123456789` | አጠቃቀም: `/approve 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_user_id = int(context.args[0])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=get_approval_message(),
            parse_mode=ParseMode.MARKDOWN
        )
        if target_user_id in registry_map:
            registry_map[target_user_id]["status"] = "APPROVED"
        await update.message.reply_text(
            f"✅ Approved user `{target_user_id}` | ተጠቃሚው ጸድቋል",
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"✅ Admin approved user {target_user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/reject 123456789 reason` | አጠቃቀም: `/reject 123456789 ምክንያት`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_user_id = int(context.args[0])
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=get_rejection_message(reason),
            parse_mode=ParseMode.MARKDOWN
        )
        if target_user_id in registry_map:
            registry_map[target_user_id]["status"] = "REJECTED"
        await update.message.reply_text(
            f"❌ Rejected user `{target_user_id}` | ተጠቃሚው ውድቅ ተደርጓል",
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"❌ Admin rejected user {target_user_id}: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/reply 123456789 message` | አጠቃቀም: `/reply 123456789 መልእክት`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_user_id = int(context.args[0])
    message = " ".join(context.args[1:])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"📬 *Message from Admin* | *ከአስተዳዳሪ መልእክት*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{message}"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(
            f"✅ Sent to `{target_user_id}` | መልእክት ተልኳል",
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"✅ Admin replied to user {target_user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized | ያልተፈቀደ")
        return
    pending = {uid: data for uid, data in registry_map.items() if data["status"] == "PENDING"}
    if not pending:
        await update.message.reply_text(
            "📋 No pending registrations | በመጠባበቅ ላይ ያለ ምዝገባ የለም",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    msg = (
        "📋 *Pending Registrations* | *በመጠባበቅ ላይ ያሉ ምዝገባዎች*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for uid, data in pending.items():
        ud = data["user_data"]
        msg += (
            f"🔑 `{uid}`\n"
            f"📝 {ud.get('first_name')} | 👤 {ud.get('fathers_name')}\n"
            f"🏦 {ud.get('cbe_account')}\n"
            f"───────────────\n"
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ============================
# MAIN FUNCTION
# ============================
def main():
    print("=" * 50)
    print("🤖 BOT STARTING...")
    print("=" * 50)
    
    # Create application
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, start_service)
        ],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            FATHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fathers_name)],
            MOTHERS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mothers_name)],
            CBE_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cbe_account)],
            FRONT_ID: [
                MessageHandler(filters.PHOTO, get_front_id),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_front_id)
            ],
            BACK_ID: [
                MessageHandler(filters.PHOTO, get_back_id),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_back_id)
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_photo)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Register all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("reject", admin_reject))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(conv_handler)
    
    print("✅ All handlers registered!")
    print("🚀 Bot is running...")
    print("=" * 50)
    
    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ============================
# RUN
# ============================
def run_flask():
    """Run Flask in a separate thread for Render health checks"""
    flask_app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    # Start Flask in background thread for Render
    Thread(target=run_flask, daemon=True).start()
    print("🌐 Flask health server started on port 10000")
    
    # Start the bot
    main()