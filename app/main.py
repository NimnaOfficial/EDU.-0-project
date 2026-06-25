import os
import io
import logging
from typing import Any
from infra.pptx_adapter import PPTXBuilder
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ─── DOMAIN ENGINE IMPORT ─────────────────────────────────────────────
from domain.parser import H5PParser

# ==========================================
# 1. SERVER LOGGING (Infrastructure Layer)
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# 2. PREMIUM UI/UX STRINGS (Frontend Layer)
# ==========================================
WELCOME_MSG = (
    "⚡ <b>EDU. 0 — Core Engine</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Your advanced suite for transforming educational architecture.\n\n"
    "<b>Available Modules:</b>\n"
    "🔸 <i>Extract & Convert:</i> H5P ➔ PPTX / PDF\n"
    "🔸 <i>Compile & Merge:</i> Stitch PDFs & Slide Decks\n"
    "🔸 <i>Reverse Engineer:</i> PPTX ➔ Interactive H5P\n\n"
    "<i>Select a module below, or simply drop a file into this chat to begin.</i>"
)

GUIDE_MSG = (
    "📚 <b>Command Center Guide</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<b>1. Auto-Detect:</b> Drag and drop an <code>.h5p</code> or <code>.pptx</code> file directly here. The engine will auto-detect the optimal conversion path.\n"
    "<b>2. Batch Processing:</b> Use the Merge module to queue multiple documents in memory before compiling.\n"
    "<b>3. UI Configuration:</b> Access layout settings via the inline module menus.\n\n"
    "<i>System Status: 🟢 Online & Ready</i>"
)

# ==========================================
# 3. INTERACTIVE WIDGETS
# ==========================================
def build_main_menu() -> InlineKeyboardMarkup:
    """Builds a modern, clean inline keyboard dashboard."""
    keyboard = [
        [InlineKeyboardButton("📤 Extract H5P to PDF/PPTX", callback_data='menu_convert')],
        [InlineKeyboardButton("🗂️ Compile & Merge Documents", callback_data='menu_merge')],
        [InlineKeyboardButton("🔄 Reverse Engineer to H5P", callback_data='menu_reverse')],
        [InlineKeyboardButton("⚙️ System Guide & Help", callback_data='menu_guide')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 4. CORE ROUTING HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires when the user initializes the bot."""
    if update.message:
        await update.message.reply_text(
            text=WELCOME_MSG, 
            reply_markup=build_main_menu(), 
            parse_mode='HTML'
        )

async def inline_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes all UI button clicks flawlessly."""
    query = update.callback_query
    if not query:
        return
        
    await query.answer() 
    
    if query.data == 'menu_guide':
        await query.edit_message_text(
            text=GUIDE_MSG, 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return to Main Dashboard", callback_data='menu_back')]]),
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
            text=f"⏳ <i>Loading module [{query.data}]...</i>\n\nPlease upload your target file.",
            parse_mode='HTML'
        )

async def document_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches file uploads, validates format, downloads securely into RAM, 
    and routes the data stream to the Domain parser engine.
    """
    if not update.message or not update.message.document:
        return
    
    document = update.message.document
    file_name = document.file_name or "Unknown_File"
    
    # Strict File Type Validation
    if not file_name.endswith('.h5p'):
        await update.message.reply_text(
            "⚠️ <b>Unsupported Format</b>\n"
            f"You uploaded <code>{file_name}</code>.\n"
            "Currently, the engine only accepts raw <code>.h5p</code> packages for extraction.",
            parse_mode='HTML'
        )
        return

    # Fix for the "None" file size Pylance warning
    file_size_display = f"{round(document.file_size / (1024 * 1024), 2)} MB" if document.file_size else "Unknown size"

    # UI Feedback: Allocate Memory
    status_msg = await update.message.reply_text(
        f"📥 <b>Intercepted:</b> <code>{file_name}</code>\n"
        f"<i>Allocating {file_size_display} of RAM...</i>",
        parse_mode='HTML'
    )
    
    try:
        # 1. UI Feedback: Downloading
        await status_msg.edit_text(
            f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
            f"<i>Securely transferring to RAM buffer...</i>",
            parse_mode='HTML'
        )

        # Secure Telegram RAM Download
        tg_file = await context.bot.get_file(document.file_id)
        h5p_buffer = io.BytesIO()
        await tg_file.download_to_memory(out=h5p_buffer)
        h5p_buffer.seek(0) 
        
        # 2. UI Feedback: Parsing
        await status_msg.edit_text(
            f"⚙️ <b>Processing:</b> <code>{file_name}</code>\n"
            f"<i>Decompressing architecture and validating internal JSON schemas...</i>",
            parse_mode='HTML'
        )
        
        # Invoke the Domain Engine (Called only ONCE!)
        parsed_data = await H5PParser.extract_architecture(h5p_buffer)
        asset_count = len(parsed_data.raw_assets)
        
        # 3. UI Feedback: Compiling
        await status_msg.edit_text(
            f"✅ <b>Extraction Complete</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Title:</b> {parsed_data.metadata.title}\n"
            f"<b>Type:</b> {parsed_data.metadata.mainLibrary}\n"
            f"<b>Assets:</b> {asset_count} media files mapped\n\n"
            f"<i>🏗️ Compiling native PPTX presentation...</i>",
            parse_mode='HTML'
        )
        
        # Invoke the Infrastructure Engine (Phase 3)
        pptx_stream = await PPTXBuilder.build_presentation(parsed_data)
        
        # Format the new filename cleanly (removing spaces and illegal characters)
        safe_title = parsed_data.metadata.title.replace(' ', '_').replace('/', '_')
        output_filename = f"{safe_title}_EDU_0.pptx"

        # 4. UI Feedback: Dispatching
        await status_msg.edit_text(
            f"🚀 <b>Compilation Successful!</b>\n"
            f"<i>Dispatching <code>{output_filename}</code> to your chat...</i>",
            parse_mode='HTML'
        )

        # Ensure chat exists for strict type-checking (Satisfies Pylance)
        if not update.effective_chat:
            return

        # Phase 4: Deliver the Final File (With extended timeouts for large files)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pptx_stream,
            filename=output_filename,
            caption=(
                f"🎯 <b>Transformation Complete</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 <b>Original:</b> <code>{file_name}</code>\n"
                f"📊 <b>Embedded:</b> {asset_count} high-res assets\n"
                f"⚡ <i>Powered by EDU. 0 Engine</i>"
            ),
            parse_mode='HTML',
            read_timeout=120,   # ◄── Tells Python to wait patiently for large uploads
            write_timeout=120   # ◄── Prevents timeout exceptions
        )
        
        # Clean up the chat by safely deleting the loading status message
        try:
            await status_msg.delete()
        except Exception as delete_err:
            logger.warning(f"Could not delete status message: {delete_err}")
        
    except ValueError as e:
        await status_msg.edit_text(
            f"❌ <b>Extraction Failed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>{str(e)}</i>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Unexpected pipeline error: {e}")
        await status_msg.edit_text(
            f"⚠️ <b>System Anomaly</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"An unexpected error occurred during the conversion pipeline. Please check system logs.",
            parse_mode='HTML'
        )

# ==========================================
# 5. FAILSAFE ARCHITECTURE
# ==========================================
async def global_error_handler(update: Any, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulletproof error catching to prevent bot crashes."""
    logger.error(msg="Exception intercepted during execution:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>System Anomaly Detected</b>\n"
            "The engine encountered an unexpected data structure. Please verify your file integrity and try again.",
            parse_mode='HTML'
        )

# ==========================================
# 6. SYSTEM INITIALIZATION
# ==========================================
if __name__ == '__main__':
    bot_token = os.environ.get("BOT_TOKEN")
    
    if not bot_token:
        logger.error("CRITICAL HALT: BOT_TOKEN environment variable is missing!")
        exit(1)

    app = ApplicationBuilder().token(bot_token).build()
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(inline_menu_router))
    app.add_handler(MessageHandler(filters.Document.ALL, document_catcher))
    app.add_error_handler(global_error_handler)
    
    logger.info("🚀 EDU. 0 Engine is online and listening...")
    app.run_polling()