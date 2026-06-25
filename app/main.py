import logging
import traceback
import html
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# 1. Setup Logging (Crucial for Docker deployment)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. UI Strings & Guides
WELCOME_MSG = (
    "👋 Welcome to <b>EDU. 0</b>!\n\n"
    "Your all-in-one suite for transforming educational content. "
    "Convert H5P to static files, merge presentations, or build interactive web apps from PDFs.\n\n"
    "<i>What would you like to do today?</i>"
)

GUIDE_MSG = (
    "📚 <b>EDU. 0 User Guide</b>\n\n"
    "<b>1. Convert Files:</b> Simply drag and drop an .h5p file into this chat.\n"
    "<b>2. Merge Documents:</b> Click 'Merge PDFs/PPTX' and upload your files one by one.\n"
    "<b>3. Customize:</b> Upload a PPTX and click the 'Customize' button that appears.\n\n"
    "<i>Need more help? Type /support</i>"
)

# 3. Main Menu UI Builder
def build_main_menu():
    keyboard = [
        [InlineKeyboardButton("📤 Convert H5P to PDF/PPTX", callback_data='menu_convert')],
        [InlineKeyboardButton("🗂️ Merge PDFs / PPTX", callback_data='menu_merge')],
        [InlineKeyboardButton("🔄 Create H5P from PPTX", callback_data='menu_reverse')],
        [InlineKeyboardButton("📖 Read User Guide", callback_data='menu_guide')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 4. Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when the user types /start"""
    await update.message.reply_text(
        text=WELCOME_MSG, 
        reply_markup=build_main_menu(), 
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all clicks on the Inline Keyboard"""
    query = update.callback_query
    await query.answer() # Acknowledges the click to Telegram
    
    if query.data == 'menu_guide':
        await query.edit_message_text(
            text=GUIDE_MSG, 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='menu_back')]]),
            parse_mode='HTML'
        )
    elif query.data == 'menu_back':
        await query.edit_message_text(
            text=WELCOME_MSG, 
            reply_markup=build_main_menu(), 
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            text=f"⚙️ <i>Initializing {query.data}... (Backend coming soon!)</i>",
            parse_mode='HTML'
        )

# 5. The Ultimate Exception Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs the error and sends a friendly message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # Friendly user-facing message (The "Educator Failsafe")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>Oops! Something hiccuped.</b>\n"
            "We encountered a slight issue processing that request. Please try again or check your file format.",
            parse_mode='HTML'
        )

# 6. Application Execution
if __name__ == '__main__':
    # Replace 'YOUR_TOKEN' with the token from @BotFather
    app = ApplicationBuilder().token('YOUR_TOKEN').build()
    
    # Route Registration
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Register the Global Error Handler
    app.add_error_handler(error_handler)
    
    logger.info("🚀 EDU. 0 Bot is officially online!")
    app.run_polling()