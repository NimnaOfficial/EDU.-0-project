import io
import logging
import asyncio
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from typing import Any

# Import our Pydantic model so we get type-checking!
from domain.parser import ParsedH5P

logger = logging.getLogger(__name__)

class PPTXBuilder:
    """
    Advanced Infrastructure logic for generating PowerPoint files.
    Constructs slides, injects media from RAM, and applies modern formatting.
    """

    @staticmethod
    async def build_presentation(h5p_data: ParsedH5P) -> io.BytesIO:
        """
        Takes the parsed H5P Domain object and compiles a PPTX file in memory.
        Runs asynchronously to prevent server lag.
        """
        try:
            return await asyncio.to_thread(PPTXBuilder._compile_sync, h5p_data)
        except Exception as e:
            logger.error(f"Failed to build PPTX infrastructure: {str(e)}")
            raise

    @staticmethod
    def _compile_sync(data: ParsedH5P) -> io.BytesIO:
        """The core synchronous engine that manipulates the PPTX XML."""
        logger.info(f"Initiating PPTX build sequence for: {data.metadata.title}")
        
        # 1. Initialize a blank Presentation
        prs = Presentation()
        
        # 2. Build the Master Title Slide
        title_slide_layout = prs.slide_layouts[0]  # Title slide layout
        blank_slide_layout = prs.slide_layouts[6]  # Blank slide layout
        title_slide = prs.slides.add_slide(title_slide_layout)
        
        # Using : Any forces Pylance to allow dynamic attributes like .text_frame
        title: Any = title_slide.shapes.title
        subtitle: Any = title_slide.placeholders[1]

        # Pylance strict type-checking fixes
        if title and title.has_text_frame:
            title.text_frame.text = data.metadata.title
            
            # Apply basic modern styling to the title
            for paragraph in title.text_frame.paragraphs:
                paragraph.font.bold = True
                paragraph.font.size = Pt(44)
                paragraph.font.color.rgb = RGBColor(41, 128, 185) # Sleek blue

        if subtitle and subtitle.has_text_frame:
            subtitle.text_frame.text = f"Extracted from: {data.metadata.mainLibrary}\nCompiled by EDU. 0 Engine"

        # 3. Extract and Build Content Slides
        # H5P structures vary wildly. We safely check if 'presentation' is a list of slides.
        slide_array = data.content.presentation.get('slides', [])
        
        if not slide_array:
             # Fallback if the H5P wasn't a standard 'CoursePresentation'
             slide_array = [{"elements": [{"action": {"params": {"text": "Notice: Custom Interactive Module. Layout requires advanced parsing."}}}]}]

        for idx, slide_data in enumerate(slide_array):
            # Add a new blank slide for each H5P slide
            slide = prs.slides.add_slide(blank_slide_layout)
            
            # Extract the elements (text boxes, images) on this specific slide
            elements = slide_data.get('elements', [])
            
            for element in elements:
                PPTXBuilder._map_element_to_slide(slide, element, data.raw_assets)

        # 4. Save to RAM and Return Buffer
        pptx_buffer = io.BytesIO()
        prs.save(pptx_buffer)
        pptx_buffer.seek(0)
        
        logger.info("PPTX build sequence complete. Returning binary stream.")
        return pptx_buffer

    @staticmethod
    def _map_element_to_slide(slide, element: dict, raw_assets: dict):
        """Intelligently routes H5P JSON elements to PPTX shapes."""
        try:
            # Safely grab coordinate data (H5P uses percentages, PPTX uses physical Inches)
            # Default to center if coordinates are missing.
            x_pct = element.get('x', 10) / 100
            y_pct = element.get('y', 20) / 100
            w_pct = element.get('width', 80) / 100
            h_pct = element.get('height', 10) / 100

            # Convert to PowerPoint Inches (Assuming standard 10x7.5 inch slide)
            left = Inches(10 * x_pct)
            top = Inches(7.5 * y_pct)
            width = Inches(10 * w_pct)
            height = Inches(7.5 * h_pct)

            # Get the action type (Text, Image, Advanced text)
            action = element.get('action', {})
            library = action.get('library', '').split(' ')[0] # e.g., "H5P.AdvancedText"
            params = action.get('params', {})

            # --- MAP TEXT ELEMENTS ---
            if 'Text' in library:
                text_content = params.get('text', '').replace('<p>', '').replace('</p>', '').replace('<br>', '\n')
                
                # Add text box to slide
                txBox = slide.shapes.add_textbox(left, top, width, height)
                tf = txBox.text_frame
                tf.word_wrap = True
                
                p = tf.add_paragraph()
                p.text = text_content
                p.font.size = Pt(18)

            # --- MAP IMAGE ELEMENTS ---
            elif 'Image' in library:
                image_path = params.get('file', {}).get('path', '')
                
                # Retrieve the raw binary image data from our Pydantic model
                if image_path in raw_assets:
                    image_stream = io.BytesIO(raw_assets[image_path])
                    # Inject the image directly into the PPTX slide
                    slide.shapes.add_picture(image_stream, left, top, width, height)

        except Exception as e:
            logger.warning(f"Skipped rendering an element due to unknown schema: {e}")