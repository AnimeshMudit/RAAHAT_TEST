# test.py
# =========================================================
# RAAHAT Conversational System Test Harness
# =========================================================
#
# PURPOSE:
# --------
# This script tests the ENTIRE conversational pipeline:
#
#   User Input
#       ↓
#   Keyword Generation
#       ↓
#   RAG Retrieval
#       ↓
#   Prompt Assembly
#       ↓
#   Final AI Response
#
# WITHOUT:
# --------
# - login
# - signup
# - web frontend
# - Telegram
# - Supabase
#
# This is the fastest way to debug:
# - retrieval quality
# - emotional understanding
# - grounding quality
# - hallucinations
# - prompt engineering
# - crisis handling
#
# =========================================================

from app.core.knowledge import (
    load_vector_store,
    search_knowledge
)

from app.core.brain import (
    generate_search_keywords,
    get_response
)

# =========================================================
# LOAD VECTOR STORE
# =========================================================

print("\n🧠 Loading RAG knowledge base...")

vector_store = load_vector_store()

print("✅ Vector store loaded successfully.\n")

# =========================================================
# TEST CONVERSATION HISTORY
# =========================================================

history = []

# =========================================================
# MAIN LOOP
# =========================================================

while True:

    print("\n" + "=" * 80)

    query = input("USER > ").strip()

    if query.lower() in ["exit", "quit"]:
        print("\n👋 Exiting test harness...")
        break

    # =====================================================
    # STEP 1 — KEYWORD GENERATION
    # =====================================================

    print("\n[STEP 1] Keyword Generation")
    print("-" * 40)

    try:
        keywords = generate_search_keywords(query)

        print(f"Generated Keywords:")
        print(f"{keywords}")

    except Exception as e:
        print(f"❌ Keyword generation failed: {e}")
        continue

    # =====================================================
    # STEP 2 — RAG RETRIEVAL
    # =====================================================

    print("\n[STEP 2] Knowledge Retrieval")
    print("-" * 40)

    try:

        retrieved_chunks = search_knowledge(
            keywords,
            vector_store
        )

        if not retrieved_chunks:

            print("⚠️ No relevant RAG context retrieved.")

        else:

            print(f"✅ Retrieved {len(retrieved_chunks)} context chunks.\n")

            for i, chunk in enumerate(retrieved_chunks, start=1):

                print(f"\n--- CONTEXT CHUNK {i} ---\n")

                print(chunk)

                print("\n" + "-" * 60)

    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        continue

    # =====================================================
    # STEP 3 — FINAL RESPONSE GENERATION
    # =====================================================

    print("\n[STEP 3] Final Response")
    print("-" * 40)

    try:

        # -------------------------------------------------
        # IMPORTANT:
        # Check your actual get_response() signature
        # inside:
        #
        # app/core/brain.py
        #
        # If needed, adjust this call.
        # -------------------------------------------------

        response = get_response(
            query,
            history,
            vector_store
        )

        print("\n🤖 AI RESPONSE:\n")
        print(response)

    except Exception as e:

        print(f"\n❌ Response generation failed:\n{e}")
        continue

    # =====================================================
    # STEP 4 — STORE LOCAL HISTORY
    # =====================================================

    history.append({
        "role": "user",
        "content": query
    })

    history.append({
        "role": "assistant",
        "content": response
    })

    # =====================================================
    # STEP 5 — DEBUG QUESTIONS
    # =====================================================

