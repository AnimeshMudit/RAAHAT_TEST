import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def test_auth():
    email = "raahat_user_test_999@gmail.com"
    password = "SuperSecurePassword123!"

    print("Testing sign_up...")
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        print("Signup response user id:", res.user.id)
        print("Signup response session:", getattr(res, "session", None))
    except Exception as e:
        print("Signup exception:", e)

    print("\nTesting sign_in_with_password...")
    try:
        res_login = supabase.auth.sign_in_with_password({"email": email, "password": password})
        print("Login success!")
        print("Session access token:", res_login.session.access_token)
        print("User ID:", res_login.user.id)
    except Exception as e:
        print("Login exception:", e)

if __name__ == "__main__":
    test_auth()
