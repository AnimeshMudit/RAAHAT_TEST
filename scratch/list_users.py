import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

res = supabase.table("users").select("id,username,is_verified,auth_provider").execute()
print(f"Total users: {len(res.data)}")
for u in res.data[:10]:
    print(u)
