from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
import uvicorn
import os

from core import memory, brain, knowledge

# Load vector database at startup if available
vector_db = None
if os.path.exists("faiss_index"):
    vector_db = knowledge.load_vector_store()
    print("Vector Vault Online! (Loaded from disk)")

app = FastAPI(title="RAAHAT API")

# Allow dashboard.html to fetch from this API running locally without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for API requests
class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    user_id: UUID
    message: str

# Existing simple HTML serving routes
@app.get("/")
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)
    
@app.get("/dashboard")
async def serve_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

# API Endpoints
@app.post("/api/login")
async def login(request: LoginRequest):
    user_id = memory.get_or_create_user(request.username, request.password)
    if user_id:
        # Provide an initial greeting for new users when their history is empty
        history = memory.fetch_history(user_id)
        if not history:
            greeting = (
                f"Welcome, {request.username}.\n\n"
                "The world asks a lot of you, but here, you don't have to be anyone but yourself.\n"
                "Your secrets are safe, your burdens are shared, and your pace is respected.\n"
                "Whenever you're ready to let it out, I'm here to listen."
            )
            memory.save_message(user_id, "ai", greeting)
            
        return {"user_id": user_id, "username": request.username}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/history")
async def get_history(user_id: UUID):
    history = memory.fetch_history(str(user_id))
    return {"history": history}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    # Save user message
    memory.save_message(str(request.user_id), "user", request.message)
    
    # Retrieve context
    context_text = ""
    if vector_db:
        # Try to search the PDF for context
        try:
            results = knowledge.search_knowledge(request.message, vector_db)
            if results:
                context_text = "\n".join(results)
        except Exception as e:
            print(f"Vector search failed: {e}")
            
    # Fetch history for context
    chat_history = memory.fetch_history(str(request.user_id))
    
    # Generate Brain Response
    response_text = brain.get_response(request.message, chat_history, context_text)
    
    # Save AI response
    memory.save_message(str(request.user_id), "ai", response_text)
    
    return {"response": response_text}

if __name__ == "__main__":
    # Runs the server on localhost port 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)