from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="RAAHAT API")

# This tells the server: "When someone visits the home page, show them index.html"
@app.get("/")
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)
    
@app.get("/dashboard")
async def serve_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

if __name__ == "__main__":
    # Runs the server on localhost port 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)