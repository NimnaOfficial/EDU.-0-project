import os
import io
import logging
import re
from telegram.ext import filters, MessageHandler
from infra.scraper_adapter import WebScraper
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

from infra.reverse_adapter import ReverseEngineer

from infra.merger_adapter import DocumentMerger
# ==========================================
# 1. SERVER LOGGING
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

HELP_MAIN_MSG = (
    "🛠️ <b>EDU. 0 — Help Center</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Welcome to the central knowledge base. Please select a module below to view its step-by-step documentation.\n\n"
    "🤖 <b>Available Commands:</b>\n"
    "<code>/start</code> — <i>Reboots the core engine & opens the main dashboard.</i>"
)

HELP_EXTRACT_MSG = (
    "📤 <b>Guide: Extract & Convert</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<i>Convert interactive .h5p web packages into static, downloadable handouts or presentations.</i>\n\n"
    "1️⃣ Click <b>'Extract H5P to PDF/PPTX'</b> on the main menu.\n"
    "2️⃣ Drag and drop your <code>.h5p</code> file into the chat.\n"
    "3️⃣ The engine will map the assets into RAM.\n"
    "4️⃣ Choose your preferred output format (<b>PPTX</b>, <b>PDF</b>, or <b>BOTH</b>).\n"
    "5️⃣ Download your perfectly scaled native documents!"
)

HELP_MERGE_MSG = (
    "🗂️ <b>Guide: Compile & Merge</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<i>Stitch multiple PDFs or PPTXs into a single master document.</i>\n\n"
    "1️⃣ Click <b>'Compile & Merge'</b> on the main menu.\n"
    "2️⃣ Upload your first file (e.g., <code>Doc1.pdf</code>). This <b>locks</b> the queue to that format!\n"
    "3️⃣ Upload additional files of the <i>same</i> format one by one.\n"
    "4️⃣ Check the live queue list to ensure the correct order.\n"
    "5️⃣ Click <b>'Compile Master Document'</b>.\n"
    "6️⃣ Download the stitched master file."
)

HELP_REVERSE_MSG = (
    "🔄 <b>Guide: Reverse Engineer</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<i>Turn boring static slides into high-resolution, interactive web packages.</i>\n\n"
    "1️⃣ Click <b>'Reverse Engineer to H5P'</b> on the main menu.\n"
    "2️⃣ Upload a standard <code>.pdf</code> or <code>.pptx</code> presentation.\n"
    "3️⃣ Wait as the bot converts and rasterizes every page into 4K resolution.\n"
    "4️⃣ Download the generated <code>.h5p</code> archive.\n"
    "5️⃣ Import it into Lumi, Moodle, or Canvas to add interactive web quizzes!"
)

HELP_CONTACT_MSG = (
    "👨‍💻 <b>Developer & Support</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<b>EDU. 0</b> was engineered with Clean Architecture to provide seamless, lag-free educational transformations.\n\n"
    "🏗️ <b>System Architect:</b> Nima\n"
    "📡 <b>Connect & Support:</b>\n"
    "💬 <b>Telegram:</b> @nimna07\n"
    "🐙 <b>GitHub:</b> <a href='https://github.com/NimnaOfficial'>NimnaOfficial</a>\n\n"
    "<i>Encountered a bug? Send a message with the file and logs!</i>"
)

# ==========================================
# 3. INTERACTIVE WIDGETS
# ==========================================
def build_main_menu() -> InlineKeyboardMarkup:
    """Builds the main dashboard buttons."""
    keyboard = [
        [InlineKeyboardButton("📤 Extract H5P to PDF/PPTX", callback_data='menu_convert')],
        [InlineKeyboardButton("🗂️ Compile & Merge Documents", callback_data='menu_merge')],
        [InlineKeyboardButton("🔄 Reverse Engineer to H5P", callback_data='menu_reverse')],
        [InlineKeyboardButton("⚙️ System Guide & Help", callback_data='menu_guide')]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_help_menu() -> InlineKeyboardMarkup:
    """Builds the sub-menu for the Help Center."""
    keyboard = [
        [InlineKeyboardButton("📖 Guide: Extract H5P", callback_data='guide_extract')],
        [InlineKeyboardButton("🗂️ Guide: Merge Files", callback_data='guide_merge')],
        [InlineKeyboardButton("🔄 Guide: Reverse Engineer", callback_data='guide_reverse')],
        [InlineKeyboardButton("👨‍💻 Developer & Contact", callback_data='guide_contact')],
        [InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data='menu_back')]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_back_to_help_btn() -> InlineKeyboardMarkup:
    """Simple back button for guide pages."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Help Center", callback_data='menu_guide')]])

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
    # --- Main Dashboard Navigation ---
    if query.data == 'menu_reverse':
        if context.user_data is not None:
            context.user_data['active_module'] = 'reverse'
        await query.edit_message_text(
            "🔄 <b>Reverse Engineer Activated</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Upload a standard .pdf or .pptx file, and I will rasterize it into a high-res interactive .h5p web package.</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='menu_back')]]),
            parse_mode='HTML'
        )
        return
        
    if query.data == 'menu_convert':
        if context.user_data is not None:
            context.user_data['active_module'] = 'convert'
        await query.edit_message_text(
            "⏳ <i>Loading Extraction module...</i>\n\nPlease upload your target .h5p file or link with embedded iframe.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='menu_back')]]),
            parse_mode='HTML'
        )
        return

    # --- HELP CENTER ROUTING ---
    if query.data == 'menu_guide':
        await query.edit_message_text(text=HELP_MAIN_MSG, reply_markup=build_help_menu(), parse_mode='HTML')
        return
    elif query.data == 'guide_extract':
        await query.edit_message_text(text=HELP_EXTRACT_MSG, reply_markup=build_back_to_help_btn(), parse_mode='HTML')
        return
    elif query.data == 'guide_merge':
        await query.edit_message_text(text=HELP_MERGE_MSG, reply_markup=build_back_to_help_btn(), parse_mode='HTML')
        return
    elif query.data == 'guide_reverse':
        await query.edit_message_text(text=HELP_REVERSE_MSG, reply_markup=build_back_to_help_btn(), parse_mode='HTML')
        return
    elif query.data == 'guide_contact':
        await query.edit_message_text(text=HELP_CONTACT_MSG, reply_markup=build_back_to_help_btn(), disable_web_page_preview=True, parse_mode='HTML')
        return

    # --- RETURN HOME ---
    if query.data == 'menu_back':
        if context.user_data is not None:
            context.user_data.clear() # Clear any active states!
        await query.edit_message_text(text=WELCOME_MSG, reply_markup=build_main_menu(), parse_mode='HTML')
        return
    else:
        await query.edit_message_text(
            text=f"⏳ <i>Loading module [{query.data}]...</i>\n\nPlease upload your target file.",
            parse_mode='HTML'
        )
        
    if query.data == 'menu_reverse':
        if context.user_data is not None:
            context.user_data['active_module'] = 'reverse' # ◄── Tell the bot we are reversing!
        await query.edit_message_text(
            "🔄 <b>Reverse Engineer Activated</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Upload a standard .pdf or .pptx file, and I will rasterize it into a high-res interactive .h5p web package.</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data='menu_back')]]),
            parse_mode='HTML'
        )
        return
        
    if query.data == 'menu_convert':
        if context.user_data is not None:
            context.user_data['active_module'] = 'convert'
        
    # --- THE MERGE DASHBOARD ROUTER ---
    if query.data == 'menu_merge':
        if context.user_data is not None:
            context.user_data['merge_queue'] = []
            context.user_data['merge_names'] = []
            context.user_data['merge_type'] = None # ◄── Add this! Tracks PDF vs PPTX
        
        await query.edit_message_text(
            "🗂️ <b>Merge Engine Activated</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Upload PDFs or PPTXs one by one in the order you want them stitched.</i>\n\n"
            "<b>Current Queue:</b> Empty",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='fmt_cancel')]]),
            parse_mode='HTML'
        )
        return

    if query.data == 'queue_merge':
        await process_merge(update, context)
        return
        
    if query.data == 'queue_clear':
        if context.user_data is not None:
            context.user_data['merge_queue'] = []
            context.user_data['merge_names'] = []
        await query.edit_message_text(
            "🗑️ <b>Queue Cleared.</b>\n<i>Upload a PDF to start a new batch.</i>", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='fmt_cancel')]]),
            parse_mode='HTML'
        )
        return
        
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

async def process_merge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Executes the final compilation of all queued documents."""
    query = update.callback_query
    if not query or context.user_data is None:
        return
        
    queue = context.user_data.get('merge_queue', [])
    queue_type = context.user_data.get('merge_type', 'pdf')
    
    if len(queue) < 2:
        await query.answer("⚠️ You need at least 2 documents to merge!", show_alert=True)
        return

    await query.edit_message_text(f"⚙️ <b>Stitching {len(queue)} {queue_type.upper()} Documents...</b>\n<i>Please wait while the master engine aligns the pages.</i>", parse_mode='HTML')

    try:
        # Route to the correct compiler
        if queue_type == 'pdf':
            master_doc = await DocumentMerger.merge_pdfs(queue)
        else:
            master_doc = await DocumentMerger.merge_pptxs(queue)
        
        if update.effective_chat:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=master_doc,
                filename=f"EDU_0_Master_Compilation.{queue_type}",
                caption=f"🎯 <b>Master {queue_type.upper()} Compilation Complete</b>\n━━━━━━━━━━━━━━━━━━━━\n📊 <b>Source Files:</b> {len(queue)}\n⚡ <i>Powered by EDU. 0 Engine</i>",
                parse_mode='HTML',
                read_timeout=120, write_timeout=120
            )

        await query.delete_message()
        context.user_data.clear()

    except Exception as e:
        logger.error(f"Merge Execution Error: {e}")
        await query.edit_message_text("⚠️ <b>Merge Failed</b>\nAn error occurred during final compilation.", parse_mode='HTML')
# ==========================================
# 4. FILE CATCHER
# ==========================================
async def document_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches file uploads, validates format, and routes to Extract or Merge engines."""
    if not update.message or not update.message.document or context.user_data is None:
        return
    
    document = update.message.document
    file_name = document.file_name or "Unknown_File"
    
    
    
    # ==========================================
    # ROUTE A: MERGE MODE (Smart Stitching)
    # ==========================================
    if 'merge_queue' in context.user_data:
        ext = file_name.split('.')[-1].lower()
        
        if ext not in ['pdf', 'pptx']:
            await update.message.reply_text("⚠️ <b>Invalid Format.</b>\nMerge mode only supports <code>.pdf</code> or <code>.pptx</code> files.", parse_mode='HTML')
            return
            
        # SMART LOCK: Prevent mixing PDFs and PPTXs
        queue_type = context.user_data.get('merge_type')
        if not queue_type:
            context.user_data['merge_type'] = ext # Lock the queue to the first file's type
        elif queue_type != ext:
            await update.message.reply_text(
                f"⚠️ <b>Format Mismatch!</b>\n"
                f"Your queue is currently locked to <b>{queue_type.upper()}</b> mode. You cannot mix formats.", 
                parse_mode='HTML'
            )
            return
            
        status_msg = await update.message.reply_text(f"📥 <i>Adding <code>{file_name}</code> to {ext.upper()} queue...</i>", parse_mode='HTML')
        
        try:
            tg_file = await context.bot.get_file(document.file_id, read_timeout=120)
            buffer = io.BytesIO()
            await tg_file.download_to_memory(out=buffer, read_timeout=120)
            
            context.user_data['merge_queue'].append(buffer)
            context.user_data['merge_names'].append(file_name)
            
            queue_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(context.user_data['merge_names'])])
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔄 Compile Master {ext.upper()}", callback_data='queue_merge')],
                [InlineKeyboardButton("🗑️ Clear Queue", callback_data='queue_clear')],
                [InlineKeyboardButton("❌ Cancel", callback_data='fmt_cancel')]
            ])
            
            await status_msg.edit_text(
                f"🗂️ <b>{ext.upper()} Queued Successfully</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Current Sequence:</b>\n"
                f"<code>{queue_list}</code>\n\n"
                f"<i>Upload another to append, or click compile.</i>",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Merge Queue Error: {e}")
            await status_msg.edit_text("⚠️ Failed to add document to RAM buffer.")
        return
    
    # ==========================================
    # ROUTE C: REVERSE ENGINEER MODE
    # ==========================================
    if context.user_data.get('active_module') == 'reverse':
        ext = file_name.split('.')[-1].lower()
        
        # Accept BOTH formats natively!
        if ext not in ['pdf', 'pptx']:
            await update.message.reply_text(
                "⚠️ <b>Invalid Format</b>\n"
                "Reverse mode supports <code>.pdf</code> and <code>.pptx</code> files.", 
                parse_mode='HTML'
            )
            return

        status_msg = await update.message.reply_text(
            f"📥 <b>Intercepted:</b> <code>{file_name}</code>\n"
            f"<i>Routing to Auto-Converter & Rasterizer engines...</i>", 
            parse_mode='HTML'
        )

        try:
            # 1. Download the static file to RAM
            tg_file = await context.bot.get_file(document.file_id, read_timeout=120)
            doc_buffer = io.BytesIO()
            await tg_file.download_to_memory(out=doc_buffer, read_timeout=120)

            await status_msg.edit_text(
                f"⚙️ <b>Rasterizing:</b> <code>{file_name}</code>\n"
                f"<i>Extracting pages and compiling dynamic HTML5 JSON blueprints...</i>", 
                parse_mode='HTML'
            )

            # 2. Invoke the Reverse Engineer Engine
            h5p_stream = await ReverseEngineer.generate_h5p(doc_buffer, file_name)
            
            # Clean filename for output
            output_filename = file_name.rsplit('.', 1)[0] + "_EDU_Interactive.h5p"

            await status_msg.edit_text("🚀 <b>Architecture Compiled!</b>\n<i>Dispatching interactive H5P package...</i>", parse_mode='HTML')

            # 3. Deliver the final interactive file
            if update.effective_chat:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=h5p_stream,
                    filename=output_filename,
                    caption="🔄 <b>Reverse Engineered Successfully</b>\n⚡ <i>Powered by EDU. 0 Engine</i>",
                    parse_mode='HTML',
                    read_timeout=120, write_timeout=120
                )

            # Cleanup
            await status_msg.delete()
            context.user_data.clear()

        except Exception as e:
            logger.error(f"Reverse Engineer Error: {e}")
            await status_msg.edit_text("⚠️ <b>System Anomaly</b>\nFailed to reverse engineer document.", parse_mode='HTML')

        return
    
    # Check if the file is an H5P file
    # Check if the file is an H5P file
    if not file_name.endswith('.h5p'):
        await update.message.reply_text("⚠️ <b>Unsupported Format</b>...", parse_mode='HTML')
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

async def link_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches text messages containing URLs and routes them to the Scraper."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    
    status_msg = await update.message.reply_text(
        "🌐 <b>Link Detected</b>\n<i>Initializing Web Scraper Engine...</i>", 
        parse_mode='HTML'
    )

    try:
        # 1. Scrape the file
        h5p_buffer, file_name = await WebScraper.fetch_h5p_from_link(text)
        
        await status_msg.edit_text(
            f"✅ <b>Download Successful:</b> <code>{file_name}</code>\n"
            f"<i>Decompressing architecture...</i>",
            parse_mode='HTML'
        )

        # 2. Inject directly into your existing Extract Engine
        parsed_data = await H5PParser.extract_architecture(h5p_buffer)
        asset_count = len(parsed_data.raw_assets)
        
        if context.user_data is not None:
            context.user_data['current_h5p'] = parsed_data
            context.user_data['current_filename'] = file_name

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
            f"<b>Assets:</b> {asset_count} media files mapped\n\n"
            f"<i>Select your preferred output format below:</i>",
            reply_markup=format_keyboard,
            parse_mode='HTML'
        )

    except PermissionError as e:
        await status_msg.edit_text(f"🛑 {str(e)}", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Scraping Error: {e}")
        await status_msg.edit_text("⚠️ <b>Scrape Failed.</b>\nThe link may be invalid or highly protected.", parse_mode='HTML')

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
    # Register Routers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(inline_menu_router))
    app.add_handler(MessageHandler(filters.Document.ALL, document_catcher))
    
    # NEW: Catch any text message that contains "http"
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'http'), link_catcher))
    app.add_error_handler(global_error_handler)
    
    logger.info("🚀 EDU. 0 Engine is online and listening...")
    app.run_polling()