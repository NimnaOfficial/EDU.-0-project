import io
import logging
import asyncio
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from domain.parser import ParsedH5P

logger = logging.getLogger(__name__)

class PDFBuilder:
    """
    Advanced Infrastructure logic for generating PDF Handouts.
    Utilizes the ReportLab Platypus engine for dynamic typography and layout.
    """

    @staticmethod
    async def build_handout(h5p_data: ParsedH5P) -> io.BytesIO:
        """
        Takes the parsed H5P Domain object and compiles a PDF file in memory.
        Runs asynchronously to prevent server lag.
        """
        try:
            return await asyncio.to_thread(PDFBuilder._compile_sync, h5p_data)
        except Exception as e:
            logger.error(f"Failed to build PDF infrastructure: {str(e)}")
            raise

    @staticmethod
    def _compile_sync(data: ParsedH5P) -> io.BytesIO:
        """The core synchronous engine that constructs the PDF layout."""
        logger.info(f"Initiating PDF build sequence for: {data.metadata.title}")
        
        pdf_buffer = io.BytesIO()
        
        # 1. Initialize the Document Template (Standard Letter Size)
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # 2. Setup Premium UI/UX Typography Styles
        styles = getSampleStyleSheet()
        
        # Custom Title Style
        styles.add(ParagraphStyle(
            name='ModernTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=HexColor("#2980b9") # EDU. 0 Signature Blue
        ))
        
        # Custom Subtitle/Metadata Style
        styles.add(ParagraphStyle(
            name='ModernSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=30,
            textColor=HexColor("#7f8c8d")
        ))

        # 3. Build the Story (The sequential list of elements on the page)
        story = []
        
        # Add Title & Metadata
        story.append(Paragraph(data.metadata.title, styles['ModernTitle']))
        story.append(Paragraph(f"Library Module: {data.metadata.mainLibrary}", styles['ModernSubtitle']))
        story.append(Paragraph("Compiled dynamically by the EDU. 0 Engine.", styles['ModernSubtitle']))
        
        # Add a visual separator
        story.append(Spacer(1, 0.2 * inch))

        # 4. Extract and Build Content
        slide_array = data.content.presentation.get('slides', [])
        
        for idx, slide_data in enumerate(slide_array):
            story.append(Paragraph(f"<b>--- Section {idx + 1} ---</b>", styles['Heading3']))
            story.append(Spacer(1, 0.1 * inch))
            
            elements = slide_data.get('elements', [])
            
            for element in elements:
                PDFBuilder._map_element_to_story(story, element, data.raw_assets, styles)
                
            story.append(Spacer(1, 0.3 * inch))

        # 5. Compile the PDF into RAM
        doc.build(story)
        pdf_buffer.seek(0)
        
        logger.info("PDF build sequence complete. Returning binary stream.")
        return pdf_buffer

    @staticmethod
    def _map_element_to_story(story: list, element: dict, raw_assets: dict, styles):
        """Intelligently routes H5P JSON elements to PDF layout objects."""
        try:
            action = element.get('action', {})
            library = action.get('library', '').split(' ')[0]
            params = action.get('params', {})

            # --- MAP TEXT ELEMENTS ---
            if 'Text' in library:
                text_content = params.get('text', '').replace('<p>', '').replace('</p>', '').replace('<br>', '<br/>')
                # ReportLab supports basic HTML tags like <b>, <i>, and <br/> natively!
                story.append(Paragraph(text_content, styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))

            # --- MAP IMAGE ELEMENTS ---
            elif 'Image' in library:
                image_path = params.get('file', {}).get('path', '')
                
                if image_path in raw_assets:
                    # ReportLab needs a file-like object
                    image_stream = io.BytesIO(raw_assets[image_path])
                    
                    # Create the image object
                    img = RLImage(image_stream)
                    
                    # Advanced UI Math: Scale the image to fit the page width seamlessly
                    max_width = 6.5 * inch # Letter width minus margins
                    if img.drawWidth > max_width:
                        aspect_ratio = max_width / float(img.drawWidth)
                        img.drawWidth = max_width
                        img.drawHeight = img.drawHeight * aspect_ratio
                        
                    story.append(img)
                    story.append(Spacer(1, 0.2 * inch))

        except Exception as e:
            logger.warning(f"Skipped rendering a PDF element due to unknown schema: {e}")