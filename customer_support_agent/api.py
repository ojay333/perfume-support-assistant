from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from llm_client import generate_draft
from rag_client import generate_grounded_reply

app = FastAPI()
class AskRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=500)
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(request: AskRequest):
    if request.user_input.strip() == "":
        raise HTTPException(status_code=422, detail="النص مطلوب")
    result = generate_grounded_reply(request.user_input)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/requests")
def create_draft(request: AskRequest):
    if request.user_input.strip() == "":
        raise HTTPException(status_code=422, detail="النص مطلوب")
    result = generate_draft(request.user_input)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result
