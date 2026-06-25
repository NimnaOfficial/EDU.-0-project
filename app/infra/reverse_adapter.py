import io
import json
import zipfile
import logging
import asyncio
import os
import tempfile
import subprocess
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class ReverseEngineer:
    """
    Advanced Infrastructure for Reverse Engineering static files into H5P Interactive Modules.
    Uses LibreOffice Headless for PPTX->PDF conversion, and PyMuPDF for Rasterization.
    """

    @staticmethod
    async def generate_h5p(document_buffer: io.BytesIO, filename: str) -> io.BytesIO:
        try:
            return await asyncio.to_thread(ReverseEngineer._build_h5p_sync, document_buffer, filename)
        except Exception as e:
            logger.error(f"Failed to reverse engineer H5P: {str(e)}")
            raise

    @staticmethod
    def _convert_pptx_to_pdf(pptx_buffer: io.BytesIO) -> io.BytesIO:
        """Silently converts PPTX to PDF in a temporary Docker directory."""
        logger.info("Initializing Headless PPTX->PDF Conversion Engine...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pptx_path = os.path.join(temp_dir, "temp.pptx")
            pdf_path = os.path.join(temp_dir, "temp.pdf")
            
            # Write the RAM buffer to a temp file
            pptx_buffer.seek(0)
            with open(pptx_path, "wb") as f:
                f.write(pptx_buffer.read())

            # Command LibreOffice to convert it silently
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", temp_dir, pptx_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if not os.path.exists(pdf_path):
                raise ValueError("PPTX to PDF headless conversion failed.")

            # Read the new PDF back into RAM
            with open(pdf_path, "rb") as f:
                pdf_buffer = io.BytesIO(f.read())
                
            return pdf_buffer

    @staticmethod
    def _build_h5p_sync(buffer: io.BytesIO, filename: str) -> io.BytesIO:
        logger.info(f"Initiating H5P Reverse Engineering for: {filename}")
        
        # 1. Route through the converter if it's a PPTX!
        if filename.lower().endswith('.pptx'):
            pdf_buffer = ReverseEngineer._convert_pptx_to_pdf(buffer)
        else:
            pdf_buffer = buffer
            
        pdf_buffer.seek(0)
        
        # 2. Rasterize Document to High-Res Images
        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        
        slide_images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            slide_images.append(pix.tobytes("jpeg"))
        doc.close()

        # 3. Generate H5P JSON Blueprints (With Lumi embedTypes fix!)
        h5p_json = {
            "title": filename.replace('.pdf', '').replace('.pptx', ''),
            "language": "en",
            "mainLibrary": "H5P.CoursePresentation",
            "embedTypes": ["div", "iframe"],
            "preloadedDependencies": [
                {"machineName": "H5P.CoursePresentation", "majorVersion": 1, "minorVersion": 25}
            ]
        }

        slides_array = []
        for i in range(len(slide_images)):
            slides_array.append({
                "elements": [],
                "slideBackgroundSelector": {
                    "imageSlideBackground": {
                        "path": f"images/slide_{i}.jpg",
                        "mime": "image/jpeg"
                    }
                }
            })

        content_json = {"presentation": {"slides": slides_array}}

        # 4. Compile the .ZIP (H5P) Archive
        h5p_buffer = io.BytesIO()
        with zipfile.ZipFile(h5p_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('h5p.json', json.dumps(h5p_json))
            zipf.writestr('content/content.json', json.dumps(content_json))
            for i, img_bytes in enumerate(slide_images):
                zipf.writestr(f'content/images/slide_{i}.jpg', img_bytes)

        h5p_buffer.seek(0)
        return h5p_buffer