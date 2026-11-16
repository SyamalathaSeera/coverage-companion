from io import BytesIO

from fastapi import HTTPException
from pypdf import PdfReader


MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 20
MAX_TEXT_CHARACTERS = 250_000


def extract_pdf_text(contents: bytes):
    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Please upload a PDF smaller than 5 MB.",
        )

    try:
        reader = PdfReader(BytesIO(contents))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Please upload a PDF without password protection.",
            )

        if len(reader.pages) > MAX_PAGES:
            raise HTTPException(
                status_code=400,
                detail="Please upload a PDF with no more than 20 pages.",
            )

        pages = []
        total_characters = 0

        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            total_characters += len(text)
            if total_characters > MAX_TEXT_CHARACTERS:
                raise HTTPException(413, "This PDF contains too much text. Use a shorter benefits summary.")

            pages.append({
                "page_number": page_number,
                "text": text,
            })

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Unable to read this PDF. Try another text-based PDF.",
        ) from error

    if not any(page["text"] for page in pages):
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found. "
                "Use a text-based PDF rather than a scanned image."
            ),
        )

    return pages
