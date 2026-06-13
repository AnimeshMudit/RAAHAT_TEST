import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

pwd = "TestPassword123!"
emails = [
    "test_user_11069@example.com",
    "test_user_61350@example.com",
    "test_user_26156@example.com",
    "test_user_25469@example.com"
]

for email in emails:
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": pwd
        })
        if res.user:
            print(f"🎉 SUCCESS! Email: {email}, Password: {pwd}")
            sys.exit(0)
    except Exception as e:
        print(f"Failed for {email}: {e}")

print("None of the accounts succeeded.")
