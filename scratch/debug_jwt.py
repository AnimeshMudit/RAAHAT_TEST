import inspect
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

auth_methods = dir(supabase.auth)
print("Auth methods:")
print([m for m in auth_methods if "user" in m])

print("\nSignature of get_user:")
try:
    print(inspect.signature(supabase.auth.get_user))
except Exception as e:
    print("Error getting signature:", e)
