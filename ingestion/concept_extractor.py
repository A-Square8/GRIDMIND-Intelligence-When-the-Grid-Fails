import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CONCEPT_PROMPT = """You are a survival knowledge analyst. Given text from a survival manual, extract concepts and relationships.

Return a JSON object. Each key is a concept, value has:
- "requires": dependencies (tools, materials, conditions)
- "related": closely related survival topics
- "see_also": loosely related topics

Return 1-3 concepts max. Only survival-relevant concepts.

TEXT:
{text}

JSON:"""


def extract_concepts_from_chunks(chunks, llm_backend, batch_delay=0.5):
    all_concepts = {}
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        if len(text.split()) < 40:
            continue

        prompt = CONCEPT_PROMPT.replace("{text}", text[:2000])

        try:
            result = llm_backend.generate(
                prompt, max_tokens=512, temperature=0.1, stream=False
            )
            if isinstance(result, str):
                parsed = _parse_json_object(result)
                _merge_concepts(all_concepts, parsed)
        except Exception as e:
            logger.warning("Concept extraction failed for chunk %d: %s", i, e)

        if (i + 1) % 10 == 0:
            logger.info(
                "Processed %d/%d chunks (%d concepts)",
                i + 1, total, len(all_concepts),
            )

        time.sleep(batch_delay)

    logger.info("Extraction complete: %d concepts from %d chunks", len(all_concepts), total)
    return all_concepts


def _parse_json_object(text):
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def _merge_concepts(target, source):
    for key, data in source.items():
        key_lower = key.lower().strip()
        if not key_lower or not isinstance(data, dict):
            continue
        if key_lower not in target:
            target[key_lower] = {"requires": [], "related": [], "see_also": []}
        for field in ["requires", "related", "see_also"]:
            existing = set(target[key_lower].get(field, []))
            new_items = data.get(field, [])
            if isinstance(new_items, list):
                existing.update(
                    i.lower().strip() for i in new_items if isinstance(i, str) and i.strip()
                )
            target[key_lower][field] = list(existing)


def save_concepts(concepts, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(concepts, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d concepts to %s", len(concepts), path)
