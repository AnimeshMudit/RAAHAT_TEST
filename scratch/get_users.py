import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

res = supabase.table("users").select("username, auth_provider").limit(10).execute()
print("Users in DB:")
for row in res.data:
    print(row)
