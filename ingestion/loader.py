
#GridMind Document Loader 

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}





def discover_files(
    base_dir: str | Path,
    extensions: set[str] | None = None,
    target_files: set[str] | list[str] | None = None,
) -> list[dict]:
    """Walk *base_dir* and return file metadata grouped by domain folder.

    Each entry is a dict with keys: ``path``, ``domain``, ``format``.
    Files directly in *base_dir* (not in a subdirectory) are assigned
    domain ``"_root"``.
    """
    base = Path(base_dir).resolve()
    if not base.is_dir():
        raise FileNotFoundError(f"Base directory not found: {base}")

    exts = extensions or SUPPORTED_EXTENSIONS
    target_set = set(target_files) if target_files else None
    files: list[dict] = []

    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        if target_set is not None and str(path) not in target_set:
            continue

        try:
            relative = path.relative_to(base)
            domain = relative.parts[0] if len(relative.parts) > 1 else "_root"
        except ValueError:
            domain = "_root"

        files.append({
            "path": str(path),
            "domain": domain,
            "format": path.suffix.lower().lstrip("."),
        })

    logger.info("Discovered %d files across %s", len(files), base)
    return files



def _clean_text(text: str) -> str:

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    return text.strip()


def _extract_pdf(path: str) -> str:

    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            except Exception as exc:
                logger.warning("PDF page %d failed in %s: %s", i, path, exc)
    return _clean_text("\n\n".join(pages))


def _extract_text_file(path: str) -> str:

    p = Path(path)

    for encoding in ("utf-8", "latin-1"):
        try:
            return _clean_text(p.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Cannot decode {path} with utf-8 or latin-1")


_EXTRACTORS = {
    "pdf": _extract_pdf,
    "txt": _extract_text_file,
    "md": _extract_text_file,
}


def extract_text(file_info: dict) -> str:
    """Extract clean plain text from a file described by *file_info*.

    *file_info* must contain ``path`` and ``format`` keys.
    """
    fmt = file_info["format"]
    extractor = _EXTRACTORS.get(fmt)
    if extractor is None:
        raise ValueError(f"No extractor for format '{fmt}'")
    return extractor(file_info["path"])



def load_documents(base_dir: str | Path, target_files: set[str] | list[str] | None = None) -> list[dict]:
    """Discover files under *base_dir*, extract text, return document dicts.

    Each dict has keys: ``path``, ``domain``, ``format``, ``text``.
    Files that fail extraction are skipped with a warning.
    """
    files = discover_files(base_dir, target_files=target_files)
    documents: list[dict] = []

    for i, finfo in enumerate(files, 1):
        fname = Path(finfo["path"]).name
        logger.info("[%d/%d] Loading %s …", i, len(files), fname)
        try:
            text = extract_text(finfo)
            if not text:
                logger.warning("Empty text from %s — skipping", fname)
                continue
            documents.append({**finfo, "text": text})
        except Exception as exc:
            logger.warning("Failed to extract %s: %s — skipping", fname, exc)

    logger.info(
        "Loaded %d/%d documents (total chars: %s)",
        len(documents), len(files),
        f"{sum(len(d['text']) for d in documents):,}",
    )
    return documents
