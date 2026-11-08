"""Reads text out of a photo -- handwritten or typed client notes.

Uses Tesseract OCR via pytesseract. On Streamlit Community Cloud, the
`tesseract-ocr` system package is installed automatically from packages.txt.
Locally on Windows, install it from https://github.com/UB-Mannheim/tesseract/wiki
and either put it on PATH or set TESSERACT_CMD to the tesseract.exe path.
"""
import io
import os

import pytesseract
from PIL import Image

_cmd = os.environ.get("TESSERACT_CMD")
if _cmd:
    pytesseract.pytesseract.tesseract_cmd = _cmd


def image_to_text(image_bytes: bytes) -> str:
    """Returns OCR'd text from an image. Raises a clear error if Tesseract
    isn't installed/found rather than crashing the caller unexpectedly."""
    img = Image.open(io.BytesIO(image_bytes))
    try:
        return pytesseract.image_to_string(img).strip()
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            "Tesseract OCR isn't installed on this machine. On Streamlit Cloud this is "
            "handled by packages.txt automatically. Locally, install Tesseract and set "
            "the TESSERACT_CMD environment variable to its exe path."
        ) from e


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr.py <image_path>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        print(image_to_text(f.read()))
