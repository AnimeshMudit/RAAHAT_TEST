import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

passwords = ["TestPassword123!", "password123", "password", "12345678", "123456789"]
emails = [
    "test_user12@example.com",
    "test_user100@example.com",
    "anshika7427@gmail.com",
    "2k24.cs.1d.2413437@gmail.com"
]

for email in emails:
    for pwd in passwords:
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": pwd
            })
            if res.user:
                print(f"🎉 SUCCESS! Email: {email}, Password: {pwd}")
                sys.exit(0)
        except Exception as e:
            pass

print("None of the accounts succeeded with common passwords.")
