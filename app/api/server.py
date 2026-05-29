import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uuid import UUID
from dotenv import load_dotenv

# -------------------- PATH SETUP --------------------
# This ensures Python can find your 'app' module regardless of where you run the script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv()

# -------------------- CORE IMPORTS --------------------
from app.core import memory, brain, knowledge, security, session
from app.core.security import verify_email_real
from app.core.google_auth import get_google_auth_url

# -------------------- APP INITIALIZATION --------------------
app = FastAPI(title="RAAHAT API")

STATIC_DIR = os.path.join(BASE_DIR, "static")
FAISS_DIR = os.path.join(BASE_DIR, "faiss_index")

# Mount static files to serve images, CSS, and JS assets
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]
        if ALLOWED_ORIGINS
        else []
    ),
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


def render_static_html(filename: str, replacements: dict | None = None) -> HTMLResponse:
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"{filename} not found")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    for placeholder, value in (replacements or {}).items():
        content = content.replace(f"{{{{ {placeholder} }}}}", value)
        content = content.replace(f"{{{{{placeholder}}}}}", value)

    return no_cache_html(content)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} is not configured")
    return value


def resolve_static_file(*filenames: str) -> str:
    for filename in filenames:
        file_path = os.path.join(STATIC_DIR, filename)
        if os.path.exists(file_path):
            return file_path
    raise HTTPException(
        status_code=404,
        detail=f"None of these files were found: {', '.join(filenames)}",
    )


@app.get("/")
async def serve_root():
    """Main entry point for the current frontend."""
    return await landing()


@app.get("/landing")
async def landing():
    return FileResponse(resolve_static_file("landingpage.html", "landing.html"))


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    file_name = "login.html"
    return render_static_html(
        file_name,
        {
            "SUPABASE_URL": get_required_env("SUPABASE_URL"),
            "SUPABASE_KEY": get_required_env("SUPABASE_KEY"),
        },
    )


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    file_name = "chat.html"
    return render_static_html(
        file_name,
        {
            "SUPABASE_URL": get_required_env("SUPABASE_URL"),
            "SUPABASE_KEY": get_required_env("SUPABASE_KEY"),
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias():
    """Backward-compatible alias used by some frontend flows."""
    return await chat_page()


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
                auth_provider="google",
            )
        else:
            user_id = user_record["id"]
        return {"user_id": user_id, "username": request.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/google")
async def login_google(request: Request):
    try:
        # Redirect to /auth/callback so the browser can handle PKCE code exchange
        base_url = str(request.base_url).rstrip("/")
        url = get_google_auth_url(redirect_to=f"{base_url}/auth/callback")
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback():
    """
    Serves the frontend callback page.
    Supabase uses PKCE — the browser holds the code_verifier, so the token
    exchange MUST happen client-side via the Supabase JS SDK.
    This inline page completes the exchange, syncs with /api/sync-user, then
    redirects to /chat.
    """
    supabase_url = get_required_env("SUPABASE_URL")
    supabase_key = get_required_env("SUPABASE_KEY")
    content = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Completing sign-in</title>
    <script src="https://unpkg.com/@supabase/supabase-js@2"></script>
    <style>
        body {{ font-family: Inter, Arial, sans-serif; margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f9f9ff; color: #151c27; }}
        main {{ max-width: 28rem; padding: 2rem; text-align: center; }}
    </style>
</head>
<body>
    <main>
        <p>Completing sign-in...</p>
    </main>
    <script>
        const supabaseClient = supabase.createClient({supabase_url!r}, {supabase_key!r}, {{
            auth: {{
                detectSessionInUrl: false,
                persistSession: true,
                autoRefreshToken: true,
            }},
        }});

        (async () => {{
            try {{
                const params = new URLSearchParams(window.location.search);
                const code = params.get('code');

                const {{ data: currentSession }} = await supabaseClient.auth.getSession();
                if (currentSession?.session?.user?.email) {{
                    const email = currentSession.session.user.email;
                    const syncResponse = await fetch('/api/sync-user', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ email }}),
                    }});
                    const syncData = await syncResponse.json().catch(() => null);
                    if (syncData?.user_id) {{
                        localStorage.setItem('raahat_user', JSON.stringify({{
                            user_id: syncData.user_id,
                            username: syncData.username || email,
                        }}));
                    }}
                    window.location.replace('/chat');
                    return;
                }}

                if (!code) {{
                    window.location.replace('/login');
                    return;
                }}

                const {{ data, error }} = await supabaseClient.auth.exchangeCodeForSession(code);
                if (error) throw error;

                const email = data?.session?.user?.email;
                if (email) {{
                    const syncResponse = await fetch('/api/sync-user', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ email }}),
                    }});

                    const syncData = await syncResponse.json().catch(() => null);
                    if (syncData?.user_id) {{
                        localStorage.setItem('raahat_user', JSON.stringify({{
                            user_id: syncData.user_id,
                            username: syncData.username || email,
                        }}));
                    }}
                }}

                window.location.replace('/chat');
            }} catch (error) {{
                console.error('OAuth callback failed:', error);
                window.location.replace('/login');
            }}
        }})();
    </script>
</body>
</html>"""
    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


# -------------------- TRADITIONAL AUTH API --------------------


@app.post("/api/signup")
async def signup(request: AuthRequest, http_request: Request):
    try:
        is_real, normalized_email = verify_email_real(request.username)
        if not is_real:
            raise HTTPException(
                status_code=400, detail=f"Invalid Email: {normalized_email}"
            )

        base_url = str(http_request.base_url).rstrip("/")

        memory.supabase.auth.sign_in_with_otp(
            {
                "email": normalized_email,
                "options": {"redirect_to": f"{base_url}/chat"},
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
                normalized_email, pwd, is_verified=False, auth_provider="local"
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

    if user_record.get("auth_provider") == "telegram" and not user_record.get(
        "password_hash"
    ):
        raise HTTPException(
            status_code=401, detail="This account uses Telegram sign-in."
        )

    if user_record.get("auth_provider") == "google" and not user_record.get(
        "password_hash"
    ):
        raise HTTPException(
            status_code=401,
            detail="This account uses Google sign-in. Please set a password first.",
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
        if search_query == "SKIP":
            results = []
        else:
            results = knowledge.search_knowledge(search_query, vector_db)
        context_text = "\n".join(results) if results else ""
    except Exception as e:
        print(f"Vector search failed: {e}")

    chat_history = memory.fetch_history(str(request.user_id))
    pattern_signal = session.get_pattern_signal(chat_history)
    session_summary = memory.get_session_summary(str(request.user_id))
    display_name = (
        user_record.data[0].get("display_name")
        or user_record.data[0].get("username")
        or "friend"
    )
    context_text += f"\n\nSystem Note: The user is '{display_name}'."

    response_text = brain.get_response(
        user_message=request.message,
        history=chat_history,
        context=context_text,
        pattern_signal=pattern_signal,
        session_summary=session_summary,
    )
    memory.save_message(str(request.user_id), "ai", response_text)

    return {"response": response_text}
