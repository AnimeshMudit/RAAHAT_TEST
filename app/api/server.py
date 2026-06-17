import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Request, Depends, Header, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uuid import UUID
import uuid
from dotenv import load_dotenv
import logging
import time
import json

logger = logging.getLogger(__name__)
_chat_executor = ThreadPoolExecutor(
    max_workers=min(8, os.cpu_count() or 4),
    thread_name_prefix="raahat-chat"
)

# -------------------- PATH SETUP --------------------
# This ensures Python can find your 'app' module regardless of where you run the script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv()

def is_service_role_key(token: str) -> bool:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return False
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        import base64
        data = json.loads(base64.b64decode(payload).decode('utf-8'))
        return data.get("role") == "service_role"
    except Exception:
        return False

# Audit environment configuration for exposed secret role keys
for env_var in ["SUPABASE_KEY", "SUPABASE_SERVICE_ROLE", "SERVICE_ROLE_KEY", "SERVICE_KEY", "SUPABASE_SERVICE_KEY"]:
    val = os.getenv(env_var)
    if val and is_service_role_key(val):
        logger.critical(
            "⚠️ SECURITY WARNING: Secret 'service_role' key detected in env var %s. "
            "Ensure this key is never exposed to the frontend/browser. "
            "If it has ever been committed or exposed, rotate it immediately in the Supabase Dashboard.",
            env_var
        )
        print(
            f"\n" + "!" * 80 + "\n"
            f"⚠️ SECURITY WARNING: Secret 'service_role' key detected in env var {env_var}!\n"
            "Ensure this key is never exposed to the frontend/browser.\n"
            "If it has ever been committed or exposed, rotate it immediately in the Supabase Dashboard!\n"
            "!" * 80 + "\n",
            file=sys.stderr
        )

# -------------------- CORE IMPORTS --------------------
from app.core import memory, brain, knowledge, security, session
from app.core.security import verify_email_real
from app.core.google_auth import get_google_auth_url
from app.core.metrics import (
    record_request,
    get_metrics,
    record_safety_trigger,
    record_retrieval_trigger,
    record_llm_error,
)

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


class ChatRequest(BaseModel):
    user_id: UUID | None = None
    message: str
    preferred_name: str | None = None


class SyncUserRequest(BaseModel):
    email: str


class UpdateNameRequest(BaseModel):
    user_id: UUID | None = None
    name: str


class UpdateProfileRequest(BaseModel):
    user_id: UUID | None = None
    display_name: str
    age: int | None = None


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


def get_public_origin(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host")

    if host:
        scheme = forwarded_proto or request.url.scheme
        return f"{scheme}://{host}".rstrip("/")

    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")

    return str(request.base_url).rstrip("/")


def serialize_user_profile(user_row: dict | None) -> dict:
    name = ""
    if user_row:
        name = (
            user_row.get("Name")
            or user_row.get("name")
            or user_row.get("display_name")
            or ""
        )
    trimmed_name = str(name).strip()
    return {
        "user_id": user_row.get("id") if user_row else None,
        "username": user_row.get("username") if user_row else None,
        "name": trimmed_name,
        "needs_name": not bool(trimmed_name),
    }


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
    return render_static_html("login.html")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return render_static_html("chat.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias():
    """Backward-compatible alias used by some frontend flows."""
    return await chat_page()


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page():
    return render_static_html("onboarding.html")


@app.get("/api/config")
async def get_config():
    supabase_url = get_required_env("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_anon_key:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_ANON_KEY is missing."
        )
        
    if is_service_role_key(supabase_anon_key):
        logger.critical(
            "⚠️ SECURITY VIOLATION: Blocked request to expose 'service_role' key via /api/config."
        )
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: cannot expose service_role key to client."
        )
        
    return {
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_anon_key,
    }


@app.get("/health")
async def health():
    metrics_snapshot = get_metrics()
    return {
        "status": "healthy",
        "uptime_seconds": metrics_snapshot["uptime_seconds"],
        "faiss_directory_exists": os.path.exists(FAISS_DIR),
        "performance_logging_enabled": _perf_enabled()
    }


@app.get("/metrics")
async def metrics():
    return get_metrics()



from collections import defaultdict

# Rate Limit Config (Task 11)
_LOGIN_LIMITS = defaultdict(list)
_SIGNUP_LIMITS = defaultdict(list)

LOGIN_MAX_ATTEMPTS = 5
SIGNUP_MAX_ATTEMPTS = 3
RATE_LIMIT_WINDOW = 60  # seconds (1 minute window)

def check_rate_limit(ip: str, limits_dict: dict, max_attempts: int, window: int) -> bool:
    now = time.time()
    limits_dict[ip] = [t for t in limits_dict[ip] if now - t < window]
    if len(limits_dict[ip]) >= max_attempts:
        return False
    limits_dict[ip].append(now)
    return True


# JWT Token Verification Dependency (Task 1 & Task 3)
async def get_current_user_id(request: Request, authorization: str = Header(None)) -> str:
    logger.debug("get_current_user_id dependency invoked")
    if not authorization:
        logger.debug("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    if not authorization.startswith("Bearer "):
        logger.debug("Invalid token format in authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    token = authorization.split(" ", 1)[1]

    # Dev/testing mock token bypass under strict conditions
    if token.startswith("mock-user-"):
        env = os.getenv("ENVIRONMENT", "production").lower()
        enable_test_auth = os.getenv("ENABLE_TEST_AUTH", "false").lower() == "true"
        client_ip = request.client.host if request.client else "unknown"
        is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")

        if env == "development" and enable_test_auth and is_localhost:
            email = token.split("mock-user-", 1)[1]
            try:
                user_record = memory.get_user_by_email(email)
                if not user_record:
                    user_uuid = memory.create_user(
                        email=email,
                        hashed_password=None,
                        is_verified=True,
                        auth_provider="local"
                    )
                    user_record = memory.get_user_by_id(user_uuid)
                return str(user_record["id"])
            except Exception as e:
                logger.error("Mock auth lookup failed: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Mock authentication failed"
                )
        else:
            logger.warning(
                "Rejected mock token request. Conditions not met: env=%s, enable_test_auth=%s, localhost=%s",
                env, enable_test_auth, is_localhost
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mock authentication bypass not allowed in this environment"
            )

    try:
        auth_res = memory.supabase.auth.get_user(token)
        if not auth_res or not auth_res.user:
            logger.debug("supabase.auth.get_user returned empty response or empty user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        email = auth_res.user.email
        if not email:
            logger.debug("Email not found in token user data")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not found in token"
            )
        user_record = memory.get_user_by_email(email)
        if not user_record:
            user_uuid = memory.create_user(
                email=email,
                hashed_password=None,
                is_verified=True,
                auth_provider="google"
            )
            user_record = memory.get_user_by_id(user_uuid)
        return str(user_record["id"])
    except Exception as e:
        logger.error("JWT verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# -------------------- GOOGLE AUTH ENDPOINTS --------------------


@app.post("/api/sync-user")
async def sync_user(request: SyncUserRequest):
    try:
        user_record = memory.get_user_by_email(request.email)
        is_new_signup = False
        if not user_record:
            user_id = memory.create_user(
                email=request.email,
                hashed_password=None,
                is_verified=True,
                auth_provider="google",
            )
            user_record = memory.get_user_by_id(user_id)
            is_new_signup = True
        else:
            user_id = user_record["id"]
        profile = serialize_user_profile(user_record)
        profile["user_id"] = user_id
        profile["username"] = request.email
        profile["is_new_signup"] = is_new_signup
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/user-profile")
async def user_profile(user_id: UUID | None = None, authenticated_user_id: str = Depends(get_current_user_id)):
    user_record = memory.get_user_by_id(authenticated_user_id)
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")
    return serialize_user_profile(user_record)


@app.post("/api/user-name")
async def update_user_name(request: UpdateNameRequest, authenticated_user_id: str = Depends(get_current_user_id)):
    trimmed_name = request.name.strip()
    if not trimmed_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    user_record = memory.get_user_by_id(authenticated_user_id)
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")

    memory.update_user_name(authenticated_user_id, trimmed_name)
    updated_record = memory.get_user_by_id(authenticated_user_id)
    return serialize_user_profile(updated_record)


@app.post("/api/update-profile")
async def update_profile(request: UpdateProfileRequest, authenticated_user_id: str = Depends(get_current_user_id)):
    trimmed_name = request.display_name.strip()
    if not trimmed_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    user_record = memory.get_user_by_id(authenticated_user_id)
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")

    memory.update_user_name(authenticated_user_id, trimmed_name)
    updated_record = memory.get_user_by_id(authenticated_user_id)
    return serialize_user_profile(updated_record)


@app.get("/api/auth/google")
async def login_google(request: Request):
    try:
        # Redirect to /auth/callback so the browser can handle PKCE code exchange
        public_origin = get_public_origin(request)
        url = get_google_auth_url(redirect_to=f"{public_origin}/auth/callback")
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback():
    """
    Serves the frontend callback page.
    Supabase uses PKCE, so this page simply forwards the browser back to the
    login page where the frontend can complete the exchange and local sync.
    """
    content = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Completing sign-in</title>
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
        window.location.replace(window.location.origin + '/login' + window.location.search + window.location.hash);
    </script>
</body>
</html>"""
    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


# -------------------- TRADITIONAL AUTH API --------------------


@app.post("/api/signup")
async def signup(request: Request, auth_data: AuthRequest):
    # Rate Limit (Task 11)
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip, _SIGNUP_LIMITS, SIGNUP_MAX_ATTEMPTS, RATE_LIMIT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup attempts. Please try again later."
        )

    try:
        is_real, normalized_email = verify_email_real(auth_data.username)
        if not is_real:
            raise HTTPException(
                status_code=400, detail=f"Invalid Email: {normalized_email}"
            )

        # Increase password minimum length beyond 6 characters (Task 11)
        if not auth_data.password or len(auth_data.password) < 8:
            raise HTTPException(
                status_code=400, detail="Password must be at least 8 characters."
            )

        # Sign up user in Supabase Auth
        try:
            auth_res = memory.supabase.auth.sign_up({
                "email": normalized_email,
                "password": auth_data.password
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        user_id = str(auth_res.user.id)
        
        # Check if user already exists in custom users table. If not, create them.
        existing = memory.get_user_by_id(user_id)
        if not existing:
            memory.supabase.table("users").insert({
                "id": user_id,
                "username": normalized_email,
                "password_hash": None,
                "is_verified": True,
                "auth_provider": "local"
            }).execute()

        user_record = memory.get_user_by_id(user_id)
        profile = serialize_user_profile(user_record)
        profile["user_id"] = user_id
        profile["username"] = normalized_email
        profile["is_new_signup"] = True
        
        if getattr(auth_res, "session", None):
            profile["session"] = {
                "access_token": auth_res.session.access_token,
                "refresh_token": auth_res.session.refresh_token,
                "expires_in": auth_res.session.expires_in
            }
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/login")
async def login(request: Request, auth_data: AuthRequest):
    # Rate Limit (Task 11)
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip, _LOGIN_LIMITS, LOGIN_MAX_ATTEMPTS, RATE_LIMIT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    is_real, normalized_email = verify_email_real(auth_data.username)
    if not is_real:
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        auth_res = memory.supabase.auth.sign_in_with_password({
            "email": normalized_email,
            "password": auth_data.password
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials or unconfirmed account")

    user_id = str(auth_res.user.id)
    user_record = memory.get_user_by_id(user_id)
    if not user_record:
        memory.supabase.table("users").insert({
            "id": user_id,
            "username": normalized_email,
            "password_hash": None,
            "is_verified": True,
            "auth_provider": "local"
        }).execute()
        user_record = memory.get_user_by_id(user_id)

    profile = serialize_user_profile(user_record)
    profile["user_id"] = user_id
    profile["username"] = normalized_email
    profile["is_new_signup"] = bool(profile.get("needs_name"))
    
    if auth_res.session:
        profile["session"] = {
            "access_token": auth_res.session.access_token,
            "refresh_token": auth_res.session.refresh_token,
            "expires_in": auth_res.session.expires_in
        }
    return profile


# -------------------- STARTUP WARMUP --------------------


@app.on_event("startup")
async def warmup_on_startup():
    # Strict fail-fast check for test authentication backdoor (Task 1)
    env = os.getenv("ENVIRONMENT", "production").lower()
    enable_test_auth = os.getenv("ENABLE_TEST_AUTH", "false").lower() == "true"
    if enable_test_auth:
        if env != "development":
            logger.critical("FATAL: ENABLE_TEST_AUTH is enabled but ENVIRONMENT is '%s'. Test authentication bypass is strictly prohibited outside development environment.", env)
            sys.exit("CRITICAL CONFIGURATION ERROR: ENABLE_TEST_AUTH cannot be enabled outside development environment.")
        else:
            logger.warning("WARNING: ENABLE_TEST_AUTH is enabled. This developer backdoor must only be used in local development.")

    loop = asyncio.get_running_loop()

    # Launch warmup asynchronously
    loop.run_in_executor(
        _chat_executor,
        knowledge.startup_warmup,
        FAISS_DIR
    )

    logger.info("Warmup running in background.")


# -------------------- CHAT & KNOWLEDGE API --------------------


def _perf_enabled() -> bool:
    return os.getenv("PERFORMANCE_LOGGING", "false").lower() == "true" or brain.DEBUG


def _print_perf(timings: dict, label: str = "") -> None:
    header = f"[PERF]{f' {label}' if label else ''}"
    print(header)
    rows = [
        ("History Fetch", "history_fetch"),
        ("Conversation", "conversation_summary"),
        ("Safety", "safety"),
        ("Embedding", "embedding"),
        ("Retrieval", "retrieval"),
        ("Knowledge", "knowledge_formatting"),
        ("Prompt", "prompt_construction"),
        ("LLM", "llm_generation"),
        ("Formatting", "response_formatting"),
        ("Total", "total"),
    ]
    for name, key in rows:
        print(f"{name:<22}{timings.get(key, 0.0):.2f}s")


@app.get("/api/history")
async def get_history(user_id: str | None = None, authenticated_user_id: str = Depends(get_current_user_id)):
    try:
        return {"history": memory.fetch_history(authenticated_user_id)}

    except Exception:
        logger.exception("History fetch failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch history."
        )


def _run_retrieval(message: str, k: int = 5, perf_out: dict | None = None) -> str:
    try:
        t_keywords = time.perf_counter()
        search_query = brain.generate_search_keywords(message)
        keyword_time = time.perf_counter() - t_keywords
        if search_query == "SKIP":
            if perf_out is not None:
                perf_out["embedding"] = 0.0
                perf_out["retrieval"] = 0.0
                perf_out["knowledge_formatting"] = keyword_time
            return ""
        retrieval_perf: dict = {}
        results = knowledge.search_knowledge(search_query, k=k, perf_out=retrieval_perf)
        t_format = time.perf_counter()
        context_text = "\n".join(results) if results else ""
        format_time = time.perf_counter() - t_format
        if perf_out is not None:
            perf_out["embedding"] = retrieval_perf.get("embedding", 0.0)
            perf_out["retrieval"] = retrieval_perf.get("retrieval", 0.0)
            perf_out["knowledge_formatting"] = keyword_time + format_time
        return context_text
    except Exception:
        logger.exception("Vector search failed")
        if perf_out is not None:
            perf_out.setdefault("embedding", 0.0)
            perf_out.setdefault("retrieval", 0.0)
            perf_out.setdefault("knowledge_formatting", 0.0)
        return ""


def _run_crisis_eval(
    message: str,
    history: list[dict],
    perf_out: dict | None = None,
) -> dict:
    t_safety = time.perf_counter()
    result = brain.evaluate_crisis_state(message, history)
    if perf_out is not None:
        perf_out["safety"] = time.perf_counter() - t_safety
    return result


@app.post("/api/chat")
async def chat(request: ChatRequest, authenticated_user_id: str = Depends(get_current_user_id)):
    request_id = str(uuid.uuid4())[:8]
    logger.info("[REQ %s] Chat request started", request_id)
    request_start = time.time()
    start_total = time.perf_counter()
    perf: dict = {}
    try:
        user_id = authenticated_user_id
        user_record = memory.get_user_by_id(user_id)
        if not user_record:
            raise HTTPException(status_code=400, detail="User not found.")

        memory.save_message(user_id, "user", request.message)

        chat_context = memory.build_chat_context(user_id, perf_out=perf)
        chat_history = chat_context["history"]
        llm_history = chat_context["llm_history"]
        session_summary = chat_context["session_summary"]
        recurring_themes = chat_context["recurring_themes"]

        loop = asyncio.get_running_loop()
        quick_trigger = brain.safety_check(request.message)
        retrieval_k = 1 if quick_trigger else 5

        crisis_perf: dict = {}
        retrieval_perf: dict = {}
        crisis_state, context_text = await asyncio.gather(
            loop.run_in_executor(
                _chat_executor,
                _run_crisis_eval,
                request.message,
                chat_history,
                crisis_perf,
            ),
            loop.run_in_executor(
                _chat_executor,
                _run_retrieval,
                request.message,
                retrieval_k,
                retrieval_perf,
            ),
        )
        perf["safety"] = crisis_perf.get("safety", 0.0)
        perf["embedding"] = retrieval_perf.get("embedding", 0.0)
        perf["retrieval"] = retrieval_perf.get("retrieval", 0.0)
        perf["knowledge_formatting"] = retrieval_perf.get("knowledge_formatting", 0.0)

        if crisis_state["crisis_active"]:
            record_safety_trigger()

        if crisis_state["crisis_active"] and not brain.needs_psychoeducation(request.message):
            context_text = ""

        if context_text:
            record_retrieval_trigger()

        pattern_signal = session.get_pattern_signal(chat_history)
        display_name = memory.get_user_display_name(
            user_record,
            preferred_name=request.preferred_name,
        )

        llm_perf: dict = {}
        try:
            response_text = await loop.run_in_executor(
                _chat_executor,
                lambda: brain.get_response(
                    user_message=request.message,
                    history=llm_history,
                    context=context_text,
                    pattern_signal=pattern_signal,
                    session_summary=session_summary,
                    recurring_themes=recurring_themes,
                    preferred_name=display_name,
                    crisis_state=crisis_state,
                    perf_out=llm_perf,
                ),
            )
        except Exception:
            record_llm_error()
            logger.exception("Response generation failed")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate response.",
            )
        perf["prompt_construction"] = llm_perf.get("prompt_construction", 0.0)
        perf["llm_generation"] = llm_perf.get("llm_generation", 0.0)

        t_post = time.perf_counter()
        memory.save_message(user_id, "ai", response_text)
        perf["response_formatting"] = time.perf_counter() - t_post

        perf["total"] = time.perf_counter() - start_total

        if _perf_enabled():
            _print_perf(
                perf,
                label=f"[REQ {request_id}]"
            )

        record_request(
            latency=time.time() - request_start,
            success=True
        )
        logger.info("[REQ %s] Chat request completed", request_id)
        return {"response": response_text}
    except HTTPException:
        record_request(
            latency=time.time() - request_start,
            success=False
        )
        logger.exception("[REQ %s] Chat request failed", request_id)
        raise
    except Exception:
        record_request(
            latency=time.time() - request_start,
            success=False
        )
        logger.exception("[REQ %s] Chat request failed", request_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, authenticated_user_id: str = Depends(get_current_user_id)):
    request_id = str(uuid.uuid4())[:8]
    logger.info("[REQ %s] Chat request started", request_id)
    request_start = time.time()
    start_total = time.perf_counter()
    perf: dict = {}
    try:
        user_id = authenticated_user_id
        user_record = memory.get_user_by_id(user_id)
        if not user_record:
            raise HTTPException(status_code=400, detail="User not found.")

        memory.save_message(user_id, "user", request.message)

        chat_context = memory.build_chat_context(user_id, perf_out=perf)
        chat_history = chat_context["history"]
        llm_history = chat_context["llm_history"]
        session_summary = chat_context["session_summary"]
        recurring_themes = chat_context["recurring_themes"]

        loop = asyncio.get_running_loop()
        quick_trigger = brain.safety_check(request.message)
        retrieval_k = 1 if quick_trigger else 5

        crisis_perf: dict = {}
        retrieval_perf: dict = {}
        crisis_state, context_text = await asyncio.gather(
            loop.run_in_executor(
                _chat_executor,
                _run_crisis_eval,
                request.message,
                chat_history,
                crisis_perf,
            ),
            loop.run_in_executor(
                _chat_executor,
                _run_retrieval,
                request.message,
                retrieval_k,
                retrieval_perf,
            ),
        )
        perf["safety"] = crisis_perf.get("safety", 0.0)
        perf["embedding"] = retrieval_perf.get("embedding", 0.0)
        perf["retrieval"] = retrieval_perf.get("retrieval", 0.0)
        perf["knowledge_formatting"] = retrieval_perf.get("knowledge_formatting", 0.0)

        if crisis_state["crisis_active"]:
            record_safety_trigger()

        if crisis_state["crisis_active"] and not brain.needs_psychoeducation(request.message):
            context_text = ""

        if context_text:
            record_retrieval_trigger()

        pattern_signal = session.get_pattern_signal(chat_history)
        display_name = memory.get_user_display_name(
            user_record,
            preferred_name=request.preferred_name,
        )

        async def event_generator():
            full_response = []
            start_llm = time.perf_counter()
            stream_success = True
            try:
                generator = brain.get_response_stream(
                    user_message=request.message,
                    history=llm_history,
                    context=context_text,
                    pattern_signal=pattern_signal,
                    session_summary=session_summary,
                    recurring_themes=recurring_themes,
                    preferred_name=display_name,
                    crisis_state=crisis_state,
                )
                for chunk in generator:
                    full_response.append(chunk)
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except Exception:
                stream_success = False
                record_llm_error()
                logger.exception("Stream generation failed")
                yield f"data: {json.dumps({'error': 'Failed to generate response'})}\n\n"
            finally:
                perf["llm_generation"] = time.perf_counter() - start_llm
                perf["prompt_construction"] = 0.0

                t_post = time.perf_counter()
                complete_text = "".join(full_response)
                if complete_text:
                    try:
                        memory.save_message(user_id, "ai", complete_text)
                    except Exception:
                        logger.exception("Failed to save streamed response to database")
                perf["response_formatting"] = time.perf_counter() - t_post

                perf["total"] = time.perf_counter() - start_total

                if _perf_enabled():
                    _print_perf(
                        perf,
                        label=f"[STREAMING][REQ {request_id}]"
                    )
                logger.info("[REQ %s] Chat request completed", request_id)
                record_request(
                    latency=time.time() - request_start,
                    success=stream_success
                )

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except HTTPException:
        record_request(
            latency=time.time() - request_start,
            success=False
        )
        logger.exception("[REQ %s] Chat request failed", request_id)
        raise
    except Exception:
        record_request(
            latency=time.time() - request_start,
            success=False
        )
        logger.exception("[REQ %s] Chat request failed", request_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )

