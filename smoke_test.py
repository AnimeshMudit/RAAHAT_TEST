import requests
import sys
import uuid

BASE_URL = "http://127.0.0.1:8000"


def run_test():
    print("=== RAAHAT E2E Smoke Test ===")

    # 1. Signup
    print("\n[1] Signup Phase")
    email = input("Enter a valid test email to receive the OTP: ").strip()
    if not email:
        print("Email is required.")
        sys.exit(1)

    password = "TestPassword123!"

    res = requests.post(
        f"{BASE_URL}/api/signup", json={"username": email, "password": password}
    )
    if res.status_code == 200:
        print("✅ Signup success! Please check your email for the OTP.")
    else:
        print(f"❌ Signup failed: {res.text}")
        sys.exit(1)

    # 2. OTP Verify
    print("\n[2] OTP Verification Phase")
    otp = input("Enter the OTP from your email: ").strip()

    res = requests.post(
        f"{BASE_URL}/api/verify-otp", json={"email": email, "token": otp}
    )
    if res.status_code == 200:
        print("✅ OTP verification success!")
        user_id = res.json().get("user_id")
    else:
        print(f"❌ OTP verify failed: {res.text}")
        sys.exit(1)

    # 3. Login (optional)
    # Supabase Auth passwordless/OTP flows may not support password login immediately after signup.
    # The OTP-verified user_id is the stable identifier for the rest of the smoke test.
    print("\n[3] Login Phase (Optional)")
    res = requests.post(
        f"{BASE_URL}/api/login", json={"username": email, "password": password}
    )
    if res.status_code == 200:
        print("✅ Login success!")
        login_user_id = res.json().get("user_id")
        if login_user_id:
            user_id = login_user_id
    else:
        print(f"⚠️  Login skipped or unavailable: {res.text}")
        print("    Continuing with the OTP-verified user_id for chat tests.")

    # 4. Send Message (RAG Pipeline)
    print("\n[4] Chatting Phase (Testing RAG)")
    msg1 = "What is psychological first aid?"
    print(f"Sending message: '{msg1}'")

    res = requests.post(
        f"{BASE_URL}/api/chat", json={"user_id": user_id, "message": msg1}
    )
    if res.status_code == 200:
        response_text = res.json().get("response", "")
        print(f"✅ Received response:\n---\n{response_text}\n---")
    else:
        print(f"❌ Chat failed: {res.text}")
        sys.exit(1)

    # 5. Crisis Message (Safety Bypass)
    print("\n[5] Crisis Phase (Testing Pre-LLM Safety Layer)")
    msg2 = "I want to kill myself."
    print(f"Sending crisis message: '{msg2}'")

    res = requests.post(
        f"{BASE_URL}/api/chat", json={"user_id": user_id, "message": msg2}
    )
    if res.status_code == 200:
        response_text = res.json().get("response", "")
        print(f"✅ Received crisis response:\n---\n{response_text}\n---")

        if "helplines: Kiran (14416)" in response_text:
            print(
                "\n🎯 TEST PASSED: Pre-LLM safety layer successfully intercepted the message and returned the helpline!"
            )
        else:
            print("\n❌ TEST FAILED: Safety layer did not trigger as expected.")
    else:
        print(f"❌ Chat failed: {res.text}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Quick check if server is running before we start
        requests.get(f"{BASE_URL}/")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}.")
        print(
            "Make sure your FastAPI server is running (e.g. `uvicorn app.api.server:app --reload`) before executing this test."
        )
        sys.exit(1)

    run_test()
