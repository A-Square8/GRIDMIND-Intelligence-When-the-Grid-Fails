import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interface.api import GridMindAPI
from core.health import SystemHealth

logger = logging.getLogger(__name__)

app = FastAPI(title="GridMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_instance = GridMindAPI()
health_monitor = SystemHealth(llm_backend=api_instance.llm, store_dir="data/vector_store")

app.mount("/static", StaticFiles(directory="web_app"), name="static")


class QueryRequest(BaseModel):
    text: str
    top_k: int = 3
    domain: str | None = None


class PlanRequest(BaseModel):
    situation: str


class TaskUpdateRequest(BaseModel):
    task_index: int
    status: str = "done"


class ConversationRequest(BaseModel):
    conversation_id: str


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. GridMind will recover on next request."},
    )


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("web_app/index.html", "r") as f:
        return f.read()


@app.post("/api/chat")
async def chat_endpoint(req: QueryRequest):
    def generate():
        try:
            for chunk in api_instance.query(req.text, top_k=req.top_k, domain=req.domain):
                yield chunk
        except Exception as e:
            logger.error("Chat generation error: %s", e)
            yield f"[ERR] System error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/api/clear_memory")
async def clear_memory():
    api_instance.pipeline.clear_memory()
    return {"status": "cleared"}


@app.post("/api/conversations/new")
async def new_conversation():
    return api_instance.new_conversation()


@app.get("/api/conversations")
async def list_conversations():
    return api_instance.list_conversations()


@app.post("/api/conversations/load")
async def load_conversation(req: ConversationRequest):
    api_instance.set_conversation(req.conversation_id)
    history = api_instance.get_conversation(req.conversation_id)
    return {"conversation_id": req.conversation_id, "messages": history}


@app.post("/api/planner/create")
async def create_plan(req: PlanRequest):
    plan = api_instance.create_plan(req.situation)
    return plan


@app.get("/api/planner/active")
async def get_active_plan():
    plan = api_instance.get_active_plan()
    if plan:
        return plan
    return {"plan": None}


@app.post("/api/planner/update")
async def update_plan_task(req: TaskUpdateRequest):
    plan = api_instance.update_plan_task(req.task_index, req.status)
    if plan:
        return plan
    return {"error": "No active plan"}


@app.delete("/api/planner/clear")
async def clear_plan():
    return api_instance.clear_plan()


@app.get("/api/health")
async def health_check():
    return health_monitor.get_report()


@app.get("/api/system/stats")
async def system_stats():
    health = health_monitor.get_report()
    db_stats = api_instance.db.get_stats() if api_instance.db.available else {}
    return {**health, **db_stats}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
