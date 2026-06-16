import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConceptGraph:
    def __init__(self, graph_path=None):
        self.graph = {}
        if graph_path:
            self.load(graph_path)

    def load(self, path):
        p = Path(path)
        if not p.exists():
            logger.warning("Concept graph not found at %s", p)
            return False
        with open(p, "r", encoding="utf-8") as f:
            self.graph = json.load(f)
        logger.info("Loaded concept graph with %d concepts", len(self.graph))
        return True

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.graph, f, ensure_ascii=False, indent=2)

    def get_related(self, concept, depth=1):
        concept_lower = concept.lower()
        related = set()

        for key, data in self.graph.items():
            if concept_lower in key.lower() or key.lower() in concept_lower:
                related.update(data.get("requires", []))
                related.update(data.get("related", []))
                related.update(data.get("see_also", []))

        if depth > 1:
            second_level = set()
            for r in list(related):
                for key, data in self.graph.items():
                    if r.lower() in key.lower():
                        second_level.update(data.get("related", []))
            related.update(second_level)

        return list(related)

    def get_requirements(self, concept):
        concept_lower = concept.lower()
        requirements = []
        for key, data in self.graph.items():
            if concept_lower in key.lower() or key.lower() in concept_lower:
                requirements.extend(data.get("requires", []))
        return list(set(requirements))

    def format_for_context(self, query):
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        all_requirements = set()
        all_related = set()

        for word in query_words:
            for key, data in self.graph.items():
                if word in key.lower() or key.lower() in word:
                    all_requirements.update(data.get("requires", []))
                    all_related.update(data.get("related", []))
                    all_related.update(data.get("see_also", []))

        if not all_requirements and not all_related:
            return ""

        lines = ["--- LINKED CONCEPTS ---"]
        if all_requirements:
            lines.append(f"This topic requires: {', '.join(list(all_requirements)[:6])}")
        if all_related:
            lines.append(f"Related survival topics: {', '.join(list(all_related)[:8])}")
        lines.append("--- END LINKED CONCEPTS ---")
        return "\n".join(lines)

    def add_concept(self, name, requires=None, related=None, see_also=None):
        key = name.lower().strip()
        if key not in self.graph:
            self.graph[key] = {"requires": [], "related": [], "see_also": []}
        if requires:
            existing = set(self.graph[key]["requires"])
            existing.update(requires)
            self.graph[key]["requires"] = list(existing)
        if related:
            existing = set(self.graph[key]["related"])
            existing.update(related)
            self.graph[key]["related"] = list(existing)
        if see_also:
            existing = set(self.graph[key]["see_also"])
            existing.update(see_also)
            self.graph[key]["see_also"] = list(existing)
