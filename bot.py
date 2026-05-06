import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from image_processor import enhance_image, enhance_image_lite

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ─── /start command ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📸 *Photo Enhancer Bot*\n\n"
        "Mujhe koi bhi photo bhejo aur main use HD me enhance kar dunga!\n\n"
        "🔧 *Features:*\n"
        "✨ Subject Sharpening — foreground sharp hoga\n"
        "🌫️ Depth-based Blur — background depth ke hisaab se blur\n"
        "🔵 Lens Bokeh — DSLR jaisa bokeh effect\n"
        "🛡️ Edge Protection — edges clean rahenge\n"
        "🎞️ Grain Matching — realistic film grain\n"
        "🔆 HD Enhancement — CLAHE contrast boost\n\n"
        "📥 Bas photo bhejo — baaki main karonga!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── /help command ───────────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 *Help*\n\n"
        "/start — Bot shuru karo\n"
        "/help  — Yeh message\n\n"
        "📤 Photo bhejo → Bot automatically enhance karke wapas dega.\n"
        "Document ke roop me bhi photo bhej sakte ho full-quality ke liye."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── Photo ya Document handler ───────────────────────────────────────────────
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳ Photo process ho rahi hai...\n"
        "Yeh 20-40 second le sakta hai, please wait karo 🙏"
    )

    # Photo ya Document dono handle karo
    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        suffix = ".jpg"
    elif update.message.document:
        doc = update.message.document
        if not doc.mime_type.startswith("image/"):
            await msg.edit_text("❌ Sirf image files support hoti hain.")
            return
        tg_file = await doc.get_file()
        suffix = os.path.splitext(doc.file_name or ".jpg")[1] or ".jpg"
    else:
        return

    tmp_in  = tempfile.NamedTemporaryFile(suffix=suffix,  delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp_in.close()
    tmp_out.close()

    try:
        await tg_file.download_to_drive(tmp_in.name)

        # AI-based processing
        await enhance_image(tmp_in.name, tmp_out.name)

        await msg.edit_text("✅ Processing complete! Sending enhanced photo...")
        with open(tmp_out.name, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="enhanced_hd.jpg",
                caption=(
                    "🎉 *Photo Enhanced!*\n\n"
                    "✨ Subject Sharpened\n"
                    "🔵 Bokeh Applied\n"
                    "🛡️ Edges Protected\n"
                    "🔆 HD Quality\n"
                    "🎞️ Grain Matched"
                ),
                parse_mode="Markdown",
            )
        await msg.delete()

    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        await msg.edit_text(
            f"❌ Kuch error aa gaya:\n`{str(e)[:200]}`\n\n"
            "Dobara try karo ya alag photo bhejo.",
            parse_mode="Markdown",
        )
    finally:
        for path in (tmp_in.name, tmp_out.name):
            try:
                os.unlink(path)
            except Exception:
                pass


# ─── Unknown message ─────────────────────────────────────────────────────────
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Sirf photo bhejo — main enhance kar dunga!\n"
        "/start se shuru karo."
    )


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable set nahi hai!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Bot chal raha hai... 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
