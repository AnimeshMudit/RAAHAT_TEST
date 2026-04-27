import os
from dotenv import load_dotenv

load_dotenv()

def get_google_auth_url():
    """
    Generates the Google OAuth2 URL for the frontend to redirect to.
    This will be expanded once you have your Google Cloud Console credentials.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "your_client_id")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
    
    # Placeholder URL for now to allow the server to start
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&redirect_uri={redirect_uri}&"
        f"response_type=code&scope={scope}&access_type=offline"
    )
    return auth_url