import os
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()


def get_google_auth_url(redirect_to=None):
    """
    Generates the Google OAuth2 URL for the frontend to redirect to.
    This will be expanded once you have your Google Cloud Console credentials.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not configured.")

    redirect_uri = redirect_to or os.getenv("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        raise ValueError("GOOGLE_REDIRECT_URI is not configured.")

    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"

    # Placeholder URL for now to allow the server to start
    query_params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query_params}"
