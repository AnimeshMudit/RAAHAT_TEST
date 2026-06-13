import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    print("Testing get_user with empty token...")
    res = supabase.auth.get_user("")
    print("Result:", res)
except Exception as e:
    print("Exception type:", type(e))
    print("Exception details:", e)

try:
    print("\nTesting get_user with invalid format token...")
    res = supabase.auth.get_user("invalid-token")
    print("Result:", res)
except Exception as e:
    print("Exception type:", type(e))
    print("Exception details:", e)
