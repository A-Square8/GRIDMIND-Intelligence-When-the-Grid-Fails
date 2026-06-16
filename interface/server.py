from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interface.api import GridMindAPI

app = FastAPI(title="GridMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_instance = GridMindAPI()

app.mount("/static", StaticFiles(directory="web_app"), name="static")

class QueryRequest(BaseModel):
    text: str
    top_k: int = 3
    domain: str | None = None

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("web_app/index.html", "r") as f:
        return f.read()

@app.post("/api/chat")
async def chat_endpoint(req: QueryRequest):
    def generate():
        for chunk in api_instance.query(req.text, top_k=req.top_k, domain=req.domain):
            yield chunk
    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/clear_memory")
async def clear_memory():
    api_instance.pipeline.clear_memory()
    return {"status": "cleared"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
