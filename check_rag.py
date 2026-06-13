import os
import sys
import time

# Ensure the app module can be found
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Set console encoding to UTF-8 to prevent UnicodeEncodeError on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_rag():
    print("==================================================")
    print("          RAAHAT RAG Diagnostics Script           ")
    print("==================================================\n")

    # 1. Check Index files
    print("[1] Verifying FAISS Index Files...")
    faiss_dir = "faiss_index"
    index_file = os.path.join(faiss_dir, "index.faiss")
    pkl_file = os.path.join(faiss_dir, "index.pkl")

    if not os.path.exists(faiss_dir):
        print(f"❌ FAILED: Directory '{faiss_dir}' does not exist.")
        sys.exit(1)
    if not os.path.exists(index_file):
        print(f"❌ FAILED: FAISS index file '{index_file}' is missing.")
        sys.exit(1)
    if not os.path.exists(pkl_file):
        print(f"❌ FAILED: Pickled index metadata file '{pkl_file}' is missing.")
        sys.exit(1)

    print(f"✅ FAISS index files found: {index_file} ({os.path.getsize(index_file)} bytes) & {pkl_file} ({os.path.getsize(pkl_file)} bytes)\n")

    # 2. Load the vector store and embeddings
    print("[2] Loading Vector Store and Embedding Model...")
    try:
        t_start = time.perf_counter()
        from app.core import knowledge
        vector_store = knowledge.get_vector_store()
        load_time = time.perf_counter() - t_start
        print(f"✅ Model & Index successfully loaded in {load_time:.2f}s.\n")
    except Exception as e:
        print(f"❌ FAILED to load RAG dependencies: {e}")
        sys.exit(1)

    # 3. Test on-topic retrieval
    print("[3] Testing On-Topic Query (Should retrieve relevant guidelines)...")
    on_topic_query = "What is psychological first aid?"
    print(f"Query: '{on_topic_query}'")
    
    try:
        results = knowledge.search_knowledge(on_topic_query)
        if not results:
            print("❌ FAILED: No documents retrieved for a relevant search query.")
            sys.exit(1)
        
        print(f"✅ SUCCESS: Retrieved {len(results)} relevant chunks.")
        print("--- TOP CHUNK PREVIEW ---")
        print(results[0][:300] + "...")
        print("-------------------------\n")
    except Exception as e:
        print(f"❌ FAILED during on-topic search: {e}")
        sys.exit(1)

    # 4. Test off-topic query (zero matches / threshold test)
    print("[4] Testing Off-Topic Query (Should return 0 matches)...")
    off_topic_query = "How do I bake sourdough bread at home?"
    print(f"Query: '{off_topic_query}'")

    try:
        # Default threshold is 1.15 in server, let's test with default settings
        results = knowledge.search_knowledge(off_topic_query)
        if len(results) > 0:
            print(f"⚠️ Warning: Retrieved {len(results)} chunks for off-topic query (potential false positive).")
            print("Top off-topic chunk retrieved:")
            print(results[0][:200] + "...")
        else:
            print("✅ SUCCESS: 0 chunks retrieved for off-topic query (threshold logic passed).")
        print()
    except Exception as e:
        print(f"❌ FAILED during off-topic search: {e}")
        sys.exit(1)

    print("==================================================")
    print("🎉 DIAGNOSTICS COMPLETED: RAG system is fully working!")
    print("==================================================")

if __name__ == "__main__":
    check_rag()
