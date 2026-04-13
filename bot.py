"""
Kundalik.com Online Bot
O'qituvchi uchun Telegram boti
"""

import os
import logging
import threading
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

import database as db
import selenium_handler as sh


from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Jarvis is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
_ids_env = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(x) for x in _ids_env.split(",") if x.strip().isdigit()]

# ── Conversation states ───────────────────────────────────────────────────────
(
    ADD_FIO, ADD_LOGIN, ADD_PASSWORD, ADD_PARENT_LOGIN, ADD_PARENT_PASSWORD,
    EDIT_SELECT, EDIT_FIELD, EDIT_VALUE,
    DELETE_SELECT,
) = range(9)

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_allowed(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➕ O'quvchi qo'shish", "📋 Sinf ro'yxati"],
            ["⚡ HAMMANI ONLINE QILISH", "⚙️ Sozlamalar"],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)


# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Sizga ruxsat yo'q.")
        return
    await update.message.reply_text(
        "👋 Salom! Kundalik.com helper online Boti ga xush kelibsiz.\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu_keyboard(),
    )

# ── Main menu dispatcher ───────────────────────────────────────────────────────

async def menu_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    text = update.message.text

    if text == "📋 Sinf ro'yxati":
        await show_list(update, ctx)
    elif text == "⚡ HAMMANI ONLINE QILISH":
        await start_online(update, ctx)
    elif text == "⚙️ Sozlamalar":
        await settings_menu(update, ctx)

# ── Show list ─────────────────────────────────────────────────────────────────

async def show_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    students = db.get_all_students()
    if not students:
        await update.message.reply_text("📭 Ro'yxat bo'sh. Avval o'quvchi qo'shing.")
        return
    lines = ["📋 *O'quvchilar ro'yxati:*\n"]
    for i, s in enumerate(students, 1):
        lines.append(
            f"{i}. *{s['fio']}*\n"
            f"   👤 Login: `{s['login']}`\n"
            f"   👨‍👩‍👦 Ota-ona: `{s['parent']['login']}`"
        )
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

# ── ADD student conversation ───────────────────────────────────────────────────

async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text(
        "📝 Yangi o'quvchi qo'shish\n\n"
        "1️⃣ O'quvchining to'liq ismini kiriting (FIO):",
        reply_markup=cancel_keyboard(),
    )
    return ADD_FIO


async def add_fio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await _cancel(update, ctx)
    ctx.user_data["new_fio"] = update.message.text.strip()
    await update.message.reply_text("2️⃣ O'quvchining *loginini* kiriting:", parse_mode="Markdown")
    return ADD_LOGIN


async def add_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await _cancel(update, ctx)
    ctx.user_data["new_login"] = update.message.text.strip()
    await update.message.reply_text("3️⃣ O'quvchining *parolini* kiriting:", parse_mode="Markdown")
    return ADD_PASSWORD


async def add_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await _cancel(update, ctx)
    ctx.user_data["new_password"] = update.message.text.strip()
    await update.message.reply_text("4️⃣ *Ota-onaning loginini* kiriting:", parse_mode="Markdown")
    return ADD_PARENT_LOGIN


async def add_parent_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await _cancel(update, ctx)
    ctx.user_data["new_parent_login"] = update.message.text.strip()
    await update.message.reply_text("5️⃣ *Ota-onaning parolini* kiriting:", parse_mode="Markdown")
    return ADD_PARENT_PASSWORD


async def add_parent_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await _cancel(update, ctx)
    ctx.user_data["new_parent_password"] = update.message.text.strip()

    ud = ctx.user_data
    success = db.add_student(
        fio=ud["new_fio"],
        login=ud["new_login"],
        password=ud["new_password"],
        parent_login=ud["new_parent_login"],
        parent_password=ud["new_parent_password"],
    )
    if success:
        await update.message.reply_text(
            f"✅ *{ud['new_fio']}* muvaffaqiyatli qo'shildi!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            "⚠️ Bu login allaqachon mavjud. Boshqa login kiriting.",
            reply_markup=main_menu_keyboard(),
        )
    ctx.user_data.clear()
    return ConversationHandler.END

# ── ONLINE ────────────────────────────────────────────────────────────────────

async def start_online(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    students = db.get_all_students()
    if not students:
        await update.message.reply_text("📭 Ro'yxat bo'sh.")
        return

    msg = await update.message.reply_text(
        f"⚡ *{len(students)} o'quvchi* uchun online qilish boshlandi...\n"
        "Bu bir necha daqiqa olishi mumkin. Iltimos kuting ⏳",
        parse_mode="Markdown",
    )

    chat_id = update.effective_chat.id
    bot = ctx.bot

    def progress(current, total, fio, who, ok):
        icon = "✅" if ok else "❌"
        text = (
            f"{icon} [{current}/{total}] *{fio}* — {who} "
            f"{'online qilindi' if ok else 'XATO'}"
        )
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown"),
            asyncio.get_event_loop(),
        )

    def run_selenium():
        results = sh.make_all_online(students, progress_callback=progress)
        summary = (
            f"\n🏁 *Tugadi!*\n\n"
            f"👤 O'quvchilar: ✅{results['student_ok']} / ❌{results['student_fail']}\n"
            f"👨‍👩‍👦 Ota-onalar: ✅{results['parent_ok']} / ❌{results['parent_fail']}"
        )
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id=chat_id,
                text=summary,
                parse_mode="Markdown",
            ),
            asyncio.get_event_loop(),
        )

    t = threading.Thread(target=run_selenium, daemon=True)
    t.start()

# ── SETTINGS ──────────────────────────────────────────────────────────────────

async def settings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ O'quvchini tahrirlash", callback_data="edit")],
        [InlineKeyboardButton("🗑 O'quvchini o'chirish", callback_data="delete")],
    ])
    await update.message.reply_text("⚙️ *Sozlamalar:*", parse_mode="Markdown", reply_markup=keyboard)


async def settings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    students = db.get_all_students()

    if not students:
        await query.edit_message_text("📭 Ro'yxat bo'sh.")
        return ConversationHandler.END

    # Build inline keyboard of students
    buttons = [
        [InlineKeyboardButton(s["fio"], callback_data=f"{query.data}::{s['login']}")]
        for s in students
    ]
    label = "tahrirlash" if query.data == "edit" else "o'chirish"
    await query.edit_message_text(
        f"Qaysi o'quvchini {label}?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    if query.data == "edit":
        return EDIT_SELECT
    else:
        return DELETE_SELECT


# Edit flow ───────────────────────────────────────────────────────────────────

async def edit_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, login = query.data.split("::")
    ctx.user_data["edit_login"] = login
    student = db.get_student(login)

    fields = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 FIO", callback_data="field::fio")],
        [InlineKeyboardButton("🔑 O'quvchi paroli", callback_data="field::password")],
        [InlineKeyboardButton("🔑 Ota-ona login", callback_data="field::parent_login")],
        [InlineKeyboardButton("🔑 Ota-ona paroli", callback_data="field::parent_password")],
    ])
    await query.edit_message_text(
        f"✏️ *{student['fio']}* — qaysi maydonni o'zgartirish?",
        parse_mode="Markdown",
        reply_markup=fields,
    )
    return EDIT_FIELD


async def edit_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, field = query.data.split("::")
    ctx.user_data["edit_field"] = field
    labels = {
        "fio": "FIO",
        "password": "O'quvchi paroli",
        "parent_login": "Ota-ona login",
        "parent_password": "Ota-ona paroli",
    }
    await query.edit_message_text(
        f"Yangi *{labels[field]}* ni kiriting:",
        parse_mode="Markdown",
    )
    return EDIT_VALUE


async def edit_value(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text.strip()
    login = ctx.user_data["edit_login"]
    field = ctx.user_data["edit_field"]
    db.update_student(login, field, new_value)
    await update.message.reply_text(
        "✅ Ma'lumot yangilandi!",
        reply_markup=main_menu_keyboard(),
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# Delete flow ─────────────────────────────────────────────────────────────────

async def delete_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, login = query.data.split("::")
    student = db.get_student(login)
    if student:
        db.delete_student(login)
        await query.edit_message_text(f"🗑 *{student['fio']}* o'chirildi.", parse_mode="Markdown")
    else:
        await query.edit_message_text("⚠️ O'quvchi topilmadi.")
    return ConversationHandler.END


# ── Cancel ────────────────────────────────────────────────────────────────────

async def _cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def cancel_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    return await _cancel(update, ctx)


# ── App builder ───────────────────────────────────────────────────────────────

def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add student conversation
    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ O'quvchi qo'shish$"), add_start)],
        states={
            ADD_FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_fio)],
            ADD_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_login)],
            ADD_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_password)],
            ADD_PARENT_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_parent_login)],
            ADD_PARENT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_parent_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    # Settings conversation (edit + delete via inline buttons)
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_callback, pattern="^(edit|delete)$")],
        states={
            EDIT_SELECT: [CallbackQueryHandler(edit_select, pattern="^edit::")],
            EDIT_FIELD: [CallbackQueryHandler(edit_field, pattern="^field::")],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
            DELETE_SELECT: [CallbackQueryHandler(delete_select, pattern="^delete::")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(settings_conv)
    app.add_handler(
        MessageHandler(
            filters.Regex("^(📋 Sinf ro'yxati|⚡ HAMMANI ONLINE QILISH|⚙️ Sozlamalar)$"),
            menu_handler,
        )
    )

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
