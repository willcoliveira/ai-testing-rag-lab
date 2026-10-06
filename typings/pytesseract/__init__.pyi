# Type stubs for the two pytesseract functions raglab.ingest.ocr calls (pytesseract ships no
# type information, and pyright is strict on src/).
from pathlib import Path

def get_tesseract_version() -> object: ...
def image_to_string(
    image: str | Path,
    lang: str | None = None,
    config: str = "",
    nice: int = 0,
    output_type: str = "string",
    timeout: int = 0,
) -> str: ...
