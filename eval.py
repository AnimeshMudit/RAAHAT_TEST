import os
import time
import requests
from datetime import datetime

# ============================================
# CONFIG
# ============================================

BASE_URL = "http://127.0.0.1:8000"

THREAD_FOLDER = "evaluation"
OUTPUT_FOLDER = "conversation_audits"

# IMPORTANT:
# Replace this with a REAL user_id from your Supabase users table
USER_ID = "1463d0b3-efea-4248-9a3a-8ca259d4ef88"

MESSAGE_DELAY = 2

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ============================================
# LOAD THREAD FILE
# ============================================

def load_thread(filepath):

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    messages = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Remove numbering like "1. "
        if ". " in line[:4]:
            line = line.split(". ", 1)[1]

        messages.append(line)

    return messages


# ============================================
# SEND MESSAGE TO LIVE API
# ============================================

def send_message(message):

    payload = {
        "user_id": USER_ID,
        "message": message
    }

    try:

        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload
        )

        if response.status_code != 200:

            print(f"❌ API ERROR: {response.status_code}")
            print(response.text)

            return f"[ERROR {response.status_code}]"

        data = response.json()

        return data.get("response", "[NO RESPONSE FIELD FOUND]")

    except Exception as e:

        print(f"❌ Request failed: {e}")

        return "[REQUEST FAILED]"


# ============================================
# RUN THREAD
# ============================================

def run_thread(filename):

    filepath = os.path.join(THREAD_FOLDER, filename)

    messages = load_thread(filepath)

    transcript = []

    print("\n====================================")
    print(f"Running Thread: {filename}")
    print("====================================\n")

    for idx, user_message in enumerate(messages, start=1):

        print(f"USER {idx}:")
        print(user_message)
        print()

        # ============================================
        # SEND MESSAGE
        # ============================================

        bot_response = send_message(user_message)

        print("RAAHAT:")
        print(bot_response)

        print("\n------------------------------------\n")

        # ============================================
        # SAVE TRANSCRIPT
        # ============================================

        transcript.append(f"USER {idx}:")
        transcript.append(user_message)
        transcript.append("")

        transcript.append("RAAHAT:")
        transcript.append(bot_response)
        transcript.append("")

        transcript.append("------------------------------------")
        transcript.append("")

        # ============================================
        # HUMAN-LIKE DELAY
        # ============================================

        time.sleep(MESSAGE_DELAY)

    # ============================================
    # SAVE AUDIT FILE
    # ============================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = os.path.join(
        OUTPUT_FOLDER,
        f"{filename.replace('.txt', '')}_{timestamp}.txt"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(transcript))

    print(f"\n✅ Transcript saved:")
    print(output_path)


# ============================================
# MAIN
# ============================================

def main():

    if USER_ID == "PUT-YOUR-REAL-USER-ID-HERE":

        print("\n❌ PLEASE SET A REAL USER_ID FIRST\n")

        print("Go to Supabase → users table → copy a real UUID")
        print("Then replace USER_ID in eval.py\n")

        return

    files = [
        f for f in os.listdir(THREAD_FOLDER)
        if f.endswith(".txt")
    ]

    if not files:

        print("❌ No evaluation thread files found.")

        return

    print("\n🧠 AVAILABLE THREADS:\n")

    for idx, file in enumerate(files, start=1):

        print(f"{idx}. {file}")

    print()

    choice = input("Select thread number: ")

    try:

        choice = int(choice)

        selected_file = files[choice - 1]

        run_thread(selected_file)

    except Exception as e:

        print(f"\n❌ Invalid selection: {e}")


# ============================================
# ENTRY
# ============================================

if __name__ == "__main__":
    main()