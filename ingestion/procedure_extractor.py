import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a survival knowledge extractor. Given text from a survival manual, extract step-by-step procedures.

Return a JSON array. Each procedure:
- "title": short name
- "steps": array of step strings
- "requires": tools/materials needed
- "danger": warnings or null

If no procedures found, return: []

TEXT:
{text}

JSON:"""


def extract_procedures_from_chunks(chunks, llm_backend, batch_delay=0.5):
    procedures = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        if len(text.split()) < 30:
            continue

        prompt = EXTRACTION_PROMPT.replace("{text}", text[:2000])

        try:
            result = llm_backend.generate(
                prompt, max_tokens=1024, temperature=0.1, stream=False
            )
            if isinstance(result, str):
                parsed = _parse_json_array(result)
                for proc in parsed:
                    if not proc.get("title"):
                        continue
                    proc["source_chunk"] = chunk.get("chunk_id", "")
                    proc["domain"] = chunk.get("domain", "")
                    procedures.append(proc)
        except Exception as e:
            logger.warning("Procedure extraction failed for chunk %d: %s", i, e)

        if (i + 1) % 10 == 0:
            logger.info(
                "Extracted procedures from %d/%d chunks (%d found)",
                i + 1, total, len(procedures),
            )

        time.sleep(batch_delay)

    logger.info("Extraction complete: %d procedures from %d chunks", len(procedures), total)
    return procedures


def _parse_json_array(text):
    text = text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return []


def save_procedures(procedures, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(procedures, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d procedures to %s", len(procedures), path)


def load_procedures(path):
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
