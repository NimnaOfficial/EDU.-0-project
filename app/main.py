import os
import io
import logging
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ─── CORE ENGINES ─────────────────────────────────────────────────────
from domain.parser import H5PParser
from infra.pptx_adapter import PPTXBuilder
from infra.pdf_adapter import PDFBuilder

# ==========================================
# 1. SERVER LOGGING
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# 2. USER INTERFACE (Messages)
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
    "<b>1. Auto-Detect:</b> Drag and drop an <code>.h5p</code> or <code>.pptx</code> file directly here.\n"
    "<b>2. Batch Processing:</b> Use the Merge module to queue multiple documents.\n"
    "<b>3. UI Configuration:</b> Access layout settings via the inline module menus.\n\n"
    "<i>System Status: 🟢 Online & Ready</i>"
)

def build_main_menu() -> InlineKeyboardMarkup:
    """Builds the main dashboard buttons."""
    keyboard = [
        [InlineKeyboardButton("📤 Extract H5P to PDF/PPTX", callback_data='menu_convert')],
        [InlineKeyboardButton("🗂️ Compile & Merge Documents", callback_data='menu_merge')],
        [InlineKeyboardButton("🔄 Reverse Engineer to H5P", callback_data='menu_reverse')],
        [InlineKeyboardButton("⚙️ System Guide & Help", callback_data='menu_guide')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 3. ROUTERS & COMPILERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires when the user types /start."""
    if update.message:
        await update.message.reply_text(
            text=WELCOME_MSG, 
            reply_markup=build_main_menu(), 
            parse_mode='HTML'
        )

async def inline_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes all UI button clicks."""
    query = update.callback_query
    
    # Safety guard: Ensure the click has valid data
    if not query or not query.data:
        return
        
    await query.answer() 
    
    # --- Format Selection Menu (PPTX, PDF, Both, Cancel) ---
    if query.data.startswith('fmt_'):
        format_type = query.data.split('_')[1] 
        
        if format_type == 'cancel':
            if context.user_data is not None:
                context.user_data.clear()
            await query.edit_message_text("🛑 <b>Operation Cancelled.</b>\n<i>Memory cleared. Ready for new input.</i>", parse_mode='HTML')
            return
            
        await process_compilation(update, context, format_type)
        return
    
    # --- Main Dashboard Navigation ---
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
        
async def process_compilation(update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str) -> None:
    """Handles the actual file building based on what the user clicked."""
    query = update.callback_query
    if not query or context.user_data is None:
        return
    
    # 1. Retrieve the parsed data from the bot's temporary memory
    parsed_data = context.user_data.get('current_h5p')
    original_filename = context.user_data.get('current_filename', 'Document')
    
    if not parsed_data:
        await query.edit_message_text("⚠️ <i>Session expired or data lost. Please upload the file again.</i>", parse_mode='HTML')
        return

    safe_title = parsed_data.metadata.title.replace(' ', '_').replace('/', '_')
    asset_count = len(parsed_data.raw_assets)

    await query.edit_message_text(
        f"⚙️ <b>Compiling {format_type.upper()} Format...</b>\n<i>Please wait while the engine renders the document.</i>", 
        parse_mode='HTML'
    )

    try:
        # 2. Compile and Deliver based on the button clicked
        if format_type in ['pptx', 'both']:
            pptx_stream = await PPTXBuilder.build_presentation(parsed_data)
            if update.effective_chat:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pptx_stream,
                    filename=f"{safe_title}_EDU_0.pptx",
                    caption=f"📊 <b>PPTX Compiled Successfully</b>\n<i>Embedded {asset_count} assets.</i>",
                    parse_mode='HTML',
                    read_timeout=120, write_timeout=120
                )

        if format_type in ['pdf', 'both']:
            pdf_stream = await PDFBuilder.build_handout(parsed_data)
            if update.effective_chat:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_stream,
                    filename=f"{safe_title}_EDU_0.pdf",
                    caption=f"📄 <b>PDF Compiled Successfully</b>\n<i>Embedded {asset_count} assets.</i>",
                    parse_mode='HTML',
                    read_timeout=120, write_timeout=120
                )

        # 3. Clean up the chat and the memory
        await query.delete_message()
        if context.user_data is not None:
            context.user_data.clear()

    except Exception as e:
        logger.error(f"Compilation Error: {e}")
        await query.edit_message_text("⚠️ <b>Compilation Failed</b>\nAn error occurred during rendering.", parse_mode='HTML')

# ==========================================
# 4. FILE CATCHER
# ==========================================
async def document_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches file uploads, parses the data, and shows the format menu."""
    if not update.message or not update.message.document:
        return
    
    document = update.message.document
    file_name = document.file_name or "Unknown_File"
    
    # Check if the file is an H5P file
    if not file_name.endswith('.h5p'):
        await update.message.reply_text(
            "⚠️ <b>Unsupported Format</b>\n"
            f"You uploaded <code>{file_name}</code>.\n"
            "Currently, the engine only accepts raw <code>.h5p</code> packages for extraction.",
            parse_mode='HTML'
        )
        return

    file_size_display = f"{round(document.file_size / (1024 * 1024), 2)} MB" if document.file_size else "Unknown size"

    status_msg = await update.message.reply_text(
        f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
        f"<i>Securely transferring {file_size_display} to RAM buffer...</i>",
        parse_mode='HTML'
    )
    
    try:
        # Download the file to memory
        tg_file = await context.bot.get_file(document.file_id, read_timeout=120)
        h5p_buffer = io.BytesIO()
        await tg_file.download_to_memory(out=h5p_buffer, read_timeout=120)
        h5p_buffer.seek(0)
        
        await status_msg.edit_text(
            f"⚙️ <b>Processing:</b> <code>{file_name}</code>\n"
            f"<i>Decompressing architecture and validating internal data...</i>",
            parse_mode='HTML'
        )
        
        # Parse the JSON and extract the images
        parsed_data = await H5PParser.extract_architecture(h5p_buffer)
        asset_count = len(parsed_data.raw_assets)
        
        # Save the data to the bot's temporary memory safely
        if context.user_data is not None:
            context.user_data['current_h5p'] = parsed_data
            context.user_data['current_filename'] = file_name

        # Create the buttons asking what format they want
        format_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Compile as PPTX", callback_data='fmt_pptx')],
            [InlineKeyboardButton("📄 Compile as PDF", callback_data='fmt_pdf')],
            [InlineKeyboardButton("📦 Compile BOTH", callback_data='fmt_both')],
            [InlineKeyboardButton("❌ Cancel", callback_data='fmt_cancel')]
        ])

        await status_msg.edit_text(
            f"✅ <b>Extraction Complete</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Title:</b> {parsed_data.metadata.title}\n"
            f"<b>Type:</b> {parsed_data.metadata.mainLibrary}\n"
            f"<b>Assets:</b> {asset_count} media files mapped\n\n"
            f"<i>Select your preferred output format below:</i>",
            reply_markup=format_keyboard,
            parse_mode='HTML'
        )
        
    except ValueError as e:
        await status_msg.edit_text(f"❌ <b>Extraction Failed</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>{str(e)}</i>", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Unexpected pipeline error: {e}")
        await status_msg.edit_text(f"⚠️ <b>System Anomaly</b>\nAn unexpected error occurred during extraction. Please try again.", parse_mode='HTML')

# ==========================================
# 5. ERROR HANDLER
# ==========================================
async def global_error_handler(update: Any, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches unexpected crashes so the bot doesn't die."""
    logger.error(msg="Exception intercepted during execution:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>System Anomaly Detected</b>\n"
            "The engine encountered an unexpected error. Please check your file and try again.",
            parse_mode='HTML'
        )

# ==========================================
# 6. BOOT SEQUENCE
# ==========================================
if __name__ == '__main__':
    bot_token = os.environ.get("BOT_TOKEN")
    
    if not bot_token:
        logger.error("CRITICAL HALT: BOT_TOKEN environment variable is missing!")
        exit(1)

    app = (
        ApplicationBuilder()
        .token(bot_token)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(120)
        .pool_timeout(120)
        .build()
    )
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(inline_menu_router))
    app.add_handler(MessageHandler(filters.Document.ALL, document_catcher))
    app.add_error_handler(global_error_handler)
    
    logger.info("🚀 EDU. 0 Engine is online and listening...")
    app.run_polling()