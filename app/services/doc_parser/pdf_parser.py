import os
import sys

from pypdf import PdfReader

# Add path to access core modules
sys.path.append(os.path.abspath(os.path.join("..", "..", "..")))
from app.core.s3_client import download_file_to_buffer


def parse_pdf(pdf_key: str) -> dict[str, any]:
    result = {"pdf_key": pdf_key, "text": None, "metadata": None, "page_count": None, "success": False, "error": None}

    try:
        # Download PDF directly to memory using our S3 client
        pdf_buffer = download_file_to_buffer(pdf_key)
        if pdf_buffer is None:
            result["error"] = "Failed to download PDF from S3"
            return result

        # Parse the PDF using PyPDF with in-memory buffer
        reader = PdfReader(pdf_buffer)

        # Get page count
        page_count = len(reader.pages)

        # Extract text from all pages
        text_content = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"

        # Extract metadata
        metadata = reader.metadata if reader.metadata else {}

        # Store results
        result["text"] = text_content
        result["metadata"] = metadata
        result["page_count"] = page_count
        result["success"] = True

        # Clean up memory
        pdf_buffer.close()

    except Exception as e:
        result["error"] = str(e)

    return result
