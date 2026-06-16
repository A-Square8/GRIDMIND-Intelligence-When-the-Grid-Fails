import json
import time
import uuid
import logging

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are GridMind's survival planner. Given a situation, generate a prioritized 72-hour survival plan.

SITUATION:
{situation}

AVAILABLE KNOWLEDGE:
{context}

Generate a JSON array of tasks. Each task:
- "priority": "CRITICAL" or "HIGH" or "MEDIUM" or "LOW"
- "time_window": when to do it (e.g. "0-2h", "2-6h", "Day 2")
- "task": short task name
- "details": 2-4 sentences of instructions
- "requires": array of what is needed

Order by priority then time. Include 6-10 tasks covering: immediate safety, water, shelter, fire, food, signaling.

RESPOND WITH ONLY A VALID JSON ARRAY:"""


class SurvivalPlanner:
    def __init__(self, llm_backend, retriever, db=None):
        self.llm = llm_backend
        self.retriever = retriever
        self.db = db
        self.active_plan = None

    def create_plan(self, situation):
        context_chunks = []
        for keyword in ["shelter", "water", "fire", "first aid", "food", "signal"]:
            results = self.retriever.retrieve(keyword, top_k=2)
            for r in results:
                snippet = r.get("text", "")[:200]
                if snippet:
                    context_chunks.append(snippet)

        context_text = "\n".join(context_chunks[:12]) if context_chunks else "No specific knowledge base available."

        prompt = PLANNER_PROMPT.replace("{situation}", situation)
        prompt = prompt.replace("{context}", context_text)

        result = self.llm.generate(prompt, max_tokens=2048, temperature=0.3, stream=False)

        tasks = self._parse_tasks(result)

        plan = {
            "id": str(uuid.uuid4())[:8],
            "situation": situation,
            "created_at": time.time(),
            "tasks": tasks,
        }

        self.active_plan = plan

        if self.db:
            self.db.log_event("plan_created", json.dumps({"id": plan["id"], "situation": situation}))

        return plan

    def get_active_plan(self):
        return self.active_plan

    def update_task(self, task_index, status="done"):
        if not self.active_plan:
            return None
        if 0 <= task_index < len(self.active_plan["tasks"]):
            self.active_plan["tasks"][task_index]["status"] = status

            if self.db:
                self.db.log_event("task_updated", json.dumps({
                    "plan_id": self.active_plan["id"],
                    "task_index": task_index,
                    "status": status,
                }))

        return self.active_plan

    def clear_plan(self):
        self.active_plan = None

    def _parse_tasks(self, text):
        if isinstance(text, str):
            text = text.strip()
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                try:
                    tasks = json.loads(text[start : end + 1])
                    for t in tasks:
                        t.setdefault("status", "pending")
                        t.setdefault("priority", "MEDIUM")
                        t.setdefault("time_window", "")
                        t.setdefault("task", "")
                        t.setdefault("details", "")
                        t.setdefault("requires", [])
                    return tasks
                except json.JSONDecodeError:
                    pass

        return [
            {
                "priority": "CRITICAL",
                "time_window": "0-1h",
                "task": "Assess immediate dangers",
                "details": "Survey surroundings for threats. Check for injuries. Establish safe perimeter.",
                "requires": [],
                "status": "pending",
            },
            {
                "priority": "CRITICAL",
                "time_window": "0-3h",
                "task": "Secure water source",
                "details": "Locate nearest water. Prioritize purification if tools available.",
                "requires": ["container"],
                "status": "pending",
            },
            {
                "priority": "HIGH",
                "time_window": "1-4h",
                "task": "Build emergency shelter",
                "details": "Use available materials for weather protection. Prioritize wind and rain cover.",
                "requires": ["natural materials"],
                "status": "pending",
            },
        ]
