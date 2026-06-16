import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Iterator
from core.llm_engine import create_llm_backend
from core.retriever import ContextRetriever
from core.rag_pipeline import RAGPipeline
from core.persistence import GridMindDB
from core.planner import SurvivalPlanner


class GridMindAPI:
    def __init__(self, llm_backend="ollama", model_path="", store_dir="data/vector_store"):
        if llm_backend == "llamacpp":
            self.llm = create_llm_backend(backend=llm_backend, model_path=model_path)
        else:
            self.llm = create_llm_backend(backend=llm_backend)

        self.db = GridMindDB(db_path="data/gridmind.db")
        self.retriever = ContextRetriever(store_dir=store_dir)
        self.pipeline = RAGPipeline(
            self.llm, self.retriever, prompt_path="prompts/system_prompt.txt", db=self.db
        )
        self.planner = SurvivalPlanner(self.llm, self.retriever, db=self.db)
        self.current_conversation = None

    def query(self, text, top_k=3, domain=None):
        if not self.current_conversation:
            self.current_conversation = self.db.create_conversation(title=text[:50])
            self.pipeline.set_conversation(self.current_conversation)

        return self.pipeline.query(text, top_k=top_k, domain_filter=domain)

    def new_conversation(self):
        self.current_conversation = None
        self.pipeline.clear_memory()
        return {"status": "new_conversation"}

    def set_conversation(self, conversation_id):
        self.current_conversation = conversation_id
        self.pipeline.set_conversation(conversation_id)

    def list_conversations(self):
        return self.db.list_conversations()

    def get_conversation(self, conversation_id):
        return self.db.get_conversation_history(conversation_id, limit=50)

    def create_plan(self, situation):
        return self.planner.create_plan(situation)

    def get_active_plan(self):
        return self.planner.get_active_plan()

    def update_plan_task(self, task_index, status="done"):
        return self.planner.update_task(task_index, status)

    def clear_plan(self):
        self.planner.clear_plan()
        return {"status": "plan_cleared"}
