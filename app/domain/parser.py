import io
import json
import zipfile
import logging
import asyncio
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

# ==========================================
# 1. PYDANTIC DATA MODELS (Strict Validation)
# ==========================================

class H5PMetadata(BaseModel):
    """Blueprint for the h5p.json file"""
    title: str = Field(..., description="The title of the presentation")
    mainLibrary: str = Field(..., description="E.g., H5P.CoursePresentation")

class H5PContent(BaseModel):
    """Blueprint for the content/content.json file"""
    presentation: dict = Field(..., description="The main slide array and assets")
    # We use a loose dict here because H5P slide structures vary wildly,
    # but Pydantic ensures the 'presentation' key MUST exist.

class ParsedH5P(BaseModel):
    """The final object returned to the rest of the application"""
    metadata: H5PMetadata
    content: H5PContent
    raw_assets: dict[str, bytes] = Field(default_factory=dict) # Holds images/audio in RAM


# ==========================================
# 2. THE ASYNC EXTRACTION ENGINE
# ==========================================

class H5PParser:
    """
    Advanced Domain logic for handling H5P file architecture in-memory.
    Utilizes Pydantic for validation and AsyncIO for non-blocking I/O.
    """
    
    @staticmethod
    async def extract_architecture(file_stream: io.BytesIO) -> ParsedH5P:
        """
        Unzips the H5P file in RAM, validates JSON against Pydantic models,
        and extracts required media assets dynamically.
        """
        try:
            # We run the synchronous zipfile extraction in a thread pool 
            # to prevent blocking the main asyncio event loop (Zero Lag!)
            return await asyncio.to_thread(H5PParser._process_zip_sync, file_stream)
            
        except zipfile.BadZipFile:
            logger.error("Upload rejected: The file is not a valid zip archive.")
            raise ValueError("The uploaded file is corrupted or not a valid H5P container.")
        except ValidationError as e:
            logger.error(f"Upload rejected: H5P schema validation failed. Details: {e}")
            raise ValueError("The H5P internal architecture is missing critical data.")
        except Exception as e:
            logger.error(f"Unexpected parsing error: {str(e)}")
            raise

    @staticmethod
    def _process_zip_sync(file_stream: io.BytesIO) -> ParsedH5P:
        """Synchronous helper function executed safely in a background thread."""
        with zipfile.ZipFile(file_stream, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # 1. Validate Core Files Exist
            if 'h5p.json' not in file_list or 'content/content.json' not in file_list:
                raise ValueError("Corrupted H5P: Missing required h5p.json or content.json blueprints.")
            
            # 2. Extract and Validate h5p.json (Metadata)
            with zip_ref.open('h5p.json') as meta_file:
                meta_dict = json.load(meta_file)
                metadata = H5PMetadata(**meta_dict) # Pydantic validates instantly
                
            # 3. Extract and Validate content.json (Slides/Logic)
            with zip_ref.open('content/content.json') as content_file:
                # H5P often prefixes their JSON with an invisible BOM character, 
                # we use .decode('utf-8-sig') to clean it safely.
                raw_json = content_file.read().decode('utf-8-sig') 
                content_dict = json.loads(raw_json)
                content = H5PContent(**content_dict) # Pydantic validates instantly
            
            # 4. Extract Media Assets (Images/Audio) into RAM
            # We scan for the 'content/images/' directory and map them
            assets = {}
            for file_name in file_list:
                if file_name.startswith('content/images/') and file_name != 'content/images/':
                    with zip_ref.open(file_name) as asset_file:
                        # We store the raw binary of the image in the dictionary
                        assets[file_name.replace('content/', '')] = asset_file.read()

            logger.info(f"Successfully extracted H5P: '{metadata.title}' with {len(assets)} media assets.")
            
            # 5. Return the strictly typed master object
            return ParsedH5P(metadata=metadata, content=content, raw_assets=assets)