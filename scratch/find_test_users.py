import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

res = supabase.table("users").select("username").like("username", "test_user_%").execute()
print("Test users found:")
for row in res.data:
    print(row)
