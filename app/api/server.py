import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uuid import UUID

# -------------------- PATH SETUP --------------------
# This ensures Python can find your 'app' module regardless of where you run the script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# -------------------- CORE IMPORTS --------------------
from app.core import memory, brain, knowledge, security
from app.core.security import verify_email_real
from app.core.google_auth import get_google_auth_url

# -------------------- APP INITIALIZATION --------------------
app = FastAPI(title="RAAHAT API")

STATIC_DIR = os.path.join(BASE_DIR, "static")
FAISS_DIR = os.path.join(BASE_DIR, "faiss_index")

# Mount static files to serve images, CSS, and JS assets
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- DATA MODELS --------------------
class AuthRequest(BaseModel):
    username: str
    password: str


class VerifyRequest(BaseModel):
    email: str
    token: str


class ChatRequest(BaseModel):
    user_id: UUID
    message: str


class SyncUserRequest(BaseModel):
    email: str


# -------------------- UI ROUTING (FRONTEND) --------------------


def no_cache_html(content: str) -> HTMLResponse:
    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """The main entry point: Serves the Landing Page."""
    return await serve_landing()


@app.get("/landing", response_class=HTMLResponse)
async def serve_landing():
    """Serves the Sanctuary Entry Portal (landing.html)."""
    file_path = os.path.join(STATIC_DIR, "landing.html")
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="landing.html not found in static folder"
        )
    with open(file_path, "r", encoding="utf-8") as file:
        return no_cache_html(file.read())


@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    """Serves the Login/Signup Page (formerly index.html)."""
    file_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(file_path, "r", encoding="utf-8") as file:
        return no_cache_html(file.read())


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the main Wellness Dashboard."""
    file_path = os.path.join(STATIC_DIR, "dashboard.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="dashboard.html not found")
    with open(file_path, "r", encoding="utf-8") as file:
        return no_cache_html(file.read())


@app.get("/verify", response_class=HTMLResponse)
async def serve_verify():
    """Serves the OTP Verification Page."""
    file_path = os.path.join(STATIC_DIR, "verify.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="verify.html not found")
    with open(file_path, "r", encoding="utf-8") as file:
        return no_cache_html(file.read())


# -------------------- GOOGLE AUTH ENDPOINTS --------------------


@app.post("/api/sync-user")
async def sync_user(request: SyncUserRequest):
    try:
        user_record = memory.get_user_by_email(request.email)
        if not user_record:
            user_id = memory.create_user(
                email=request.email,
                hashed_password=None,
                is_verified=True,
                auth_provider="google"
            )
        else:
            user_id = user_record["id"]
        return {"user_id": user_id, "username": request.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/google")
async def login_google():
    try:
        # Redirect to /auth/callback so the browser can handle PKCE code exchange
        url = get_google_auth_url(redirect_to="http://127.0.0.1:8000/auth/callback")
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback():
    """
    Serves the frontend callback page.
    Supabase uses PKCE — the browser holds the code_verifier, so the token
    exchange MUST happen client-side via the Supabase JS SDK.
    callback.html handles the exchange, syncs with /api/sync-user, then
    redirects to /dashboard.
    """
    file_path = os.path.join(STATIC_DIR, "callback.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="callback.html not found")
    with open(file_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# -------------------- TRADITIONAL AUTH API --------------------


@app.post("/api/signup")
async def signup(request: AuthRequest):
    try:
        is_real, normalized_email = verify_email_real(request.username)
        if not is_real:
            raise HTTPException(
                status_code=400, detail=f"Invalid Email: {normalized_email}"
            )

        memory.supabase.auth.sign_in_with_otp(
            {
                "email": normalized_email,
                "options": {"redirect_to": "http://127.0.0.1:8000/dashboard"},
            }
        )

        existing = memory.get_user_by_email(normalized_email)
        if not existing:
            pwd = (
                security.get_password_hash(request.password)
                if request.password
                else None
            )
            memory.create_user(
                normalized_email,
                pwd,
                is_verified=False,
                auth_provider="local"
            )
        return {"message": "Verification code sent! Check your email."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/verify-otp")
async def verify_otp(request: VerifyRequest):
    res = None
    # Try "email" type first (used by sign_in_with_otp / magic-link flow for existing & returning users)
    for otp_type in ["email", "signup"]:
        try:
            res = memory.supabase.auth.verify_otp(
                {"email": request.email, "token": request.token, "type": otp_type}
            )
            if res.user:
                break  # Verification succeeded
        except Exception:
            continue  # Try the next type

    if res and res.user:
        memory.supabase.table("users").update({"is_verified": True}).eq(
            "username", request.email
        ).execute()
        user_rec = memory.get_user_by_email(request.email)
        user_id = (
            user_rec["id"]
            if user_rec
            else memory.create_user(request.email, "otp_user", is_verified=True)
        )
        return {"user_id": user_id, "username": request.email}

    raise HTTPException(
        status_code=400, detail="Invalid or expired OTP code. Please request a new one."
    )


@app.post("/api/login")
async def login(request: AuthRequest):
    is_real, normalized_email = verify_email_real(request.username)
    user_record = memory.get_user_by_email(normalized_email) if is_real else None

    if not user_record or not user_record.get("is_verified", False):
        raise HTTPException(
            status_code=401, detail="Invalid credentials or unverified account"
        )

    if (
        user_record.get("auth_provider") == "telegram"
        and not user_record.get("password_hash")
    ):
        raise HTTPException(
            status_code=401,
            detail="This account uses Telegram sign-in."
        )

    if (
        user_record.get("auth_provider") == "google"
        and not user_record.get("password_hash")
    ):
        raise HTTPException(
            status_code=401,
            detail="This account uses Google sign-in. Please set a password first."
        )

    try:
        res = memory.supabase.auth.sign_in_with_password(
            {"email": normalized_email, "password": request.password}
        )
        if not res.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"user_id": user_record["id"], "username": normalized_email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# -------------------- CHAT & KNOWLEDGE API --------------------


@app.get("/api/history")
async def get_history(user_id: str):
    try:
        return {"history": memory.fetch_history(user_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_record = (
        memory.supabase.table("users")
        .select("*")
        .eq("id", str(request.user_id))
        .execute()
    )
    if not user_record.data:
        raise HTTPException(status_code=400, detail="User not found.")

    memory.save_message(str(request.user_id), "user", request.message)

    context_text = ""
    try:
        vector_db = knowledge.load_vector_store(FAISS_DIR)
        search_query = brain.generate_search_keywords(request.message)
        results = knowledge.search_knowledge(search_query, vector_db)
        context_text = "\n".join(results) if results else ""
    except Exception as e:
        print(f"Vector search failed: {e}")

    chat_history = memory.fetch_history(str(request.user_id))
    display_name = user_record.data[0].get("display_name") or "Traveler"
    context_text += f"\n\nSystem Note: The user is '{display_name}'."

    response_text = brain.get_response(request.message, chat_history, context_text)
    memory.save_message(str(request.user_id), "ai", response_text)

    return {"response": response_text}
