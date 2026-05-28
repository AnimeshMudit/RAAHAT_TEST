import os
import re
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

def extract_text(file_path):
    print(f"Reading: {file_path}...")
    raw = ''
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # CLEANING: Fixes the 'broken word' issue common in WHO PDFs
                    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text) # Joins hyphenated words
                    text = re.sub(r'\s+', ' ', text) # Removes weird spacing
                    raw += text + "\n"
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return raw

def load_all_pdfs_from_folder(folder_path="data"):
    print(f"Scanning folder: {folder_path}...")
    combined_text = ""
    
    # Check every file in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            # Call your existing extract function for each file
            combined_text += extract_text(file_path) + "\n"
            
    return combined_text

def split_chunks(raw):
    """Splits plain text into micro-chunks for surgical clinical retrieval."""
    print("Chopping text into micro-chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=350,
        chunk_overlap=50,
        length_function=len
    )
    
    chunks = splitter.split_text(raw)
    return chunks

FAISS_DB_PATH = "faiss_index"

# --- EMBEDDING MODEL (Upgraded for Clinical Precision) ---
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

def _get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        show_progress=True,  # <-- Pass it directly here
        encode_kwargs={"normalize_embeddings": True}
    )

def create_vector_store(documents):
    embeddings = _get_embeddings()
    # Use default L2 — with normalized vectors, L2 and cosine rank identically
    # Score range becomes 0.0 (identical) to 2.0 (opposite), NOT 0–1
    vector_db = FAISS.from_documents(documents, embeddings)
    vector_db.save_local(FAISS_DB_PATH)
    return vector_db

def load_vector_store(path=None):
    load_path = path or FAISS_DB_PATH
    embeddings = _get_embeddings()
    return FAISS.load_local(
        load_path,
        embeddings,
        allow_dangerous_deserialization=True
        # No distance_strategy — use default L2
    )

def clean_query(query: str) -> str:
    """
    Strips redundant synonyms from a comma-separated keyword string.
    Takes only the first keyword phrase (up to 3 words) to keep FAISS search focused.
    """
    primary = query.split(',')[0].strip()
    # Limit to 3 words max to keep it focused
    words = primary.split()[:3]
    return ' '.join(words).lower()

def search_knowledge(query, vector_store, k=5, threshold=1.0):
    """
    Searches the FAISS index with a strict similarity threshold.
    With normalized vectors + L2, the score mapping is:
      - 0.0 – 0.3  → Near-exact match
      - 0.3 – 0.8  → Good clinical match  
      - 0.8 – 1.0  → Weak but possibly relevant
      - 1.0+       → Reject
    """
    cleaned = clean_query(query)
    print(f"🔍 Clean query sent to FAISS: '{cleaned}'")
    
    results = vector_store.similarity_search_with_score(cleaned, k=k)
    
    context_chunks = []
    seen = set()
    
    for doc, score in results:
        content = doc.page_content.strip()
        if content in seen:
            continue
        seen.add(content)
        
        # Preserve source filename from metadata for citation
        source = doc.metadata.get("source", "Unknown Manual")
        
        if score <= threshold:
            formatted_chunk = f"[Source: {source}]\n{doc.page_content}"
            context_chunks.append(formatted_chunk)
            print(f"✅ VALID MATCH: {source} (Score: {score:.4f})")
        else:
            print(f"❌ REJECTED: {source} (Score: {score:.4f} — too weak)")

    return context_chunks

def load_all(folder_path="data"):
    print(f"Scanning folder: {folder_path}...")
    combined_text = ""
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            combined_text += extract_text(file_path) + "\n"
            
    return combined_text
#old stuff...slow
'''def create_vector_store(chunks):
    print("Converting text into math (Vectorizing)... this might take a minute.")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Create the vector database 
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store'''


def build_vector_store_from_folder(folder_path="data"):
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder {folder_path} not found.")
        return None

    print(f"🚀 Starting Full Ingestion from: {folder_path}")
    
    all_documents = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            path = os.path.join(folder_path, filename)
            
            # Extracting text
            text = extract_text(path)
            
            if text.strip():
                # Create a Document object with metadata
                doc = Document(
                    page_content=text, 
                    metadata={"source": filename}
                )
                all_documents.append(doc)
            else:
                print(f"⚠️ Warning: {filename} is empty or unreadable.")
    
    if not all_documents:
        print("❌ No valid text found in any PDFs. Check your data folder!")
        return None
        
    # 1. Split documents — micro-chunks preserve metadata automatically
    print(f"Chopping {len(all_documents)} documents into micro-chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=350, chunk_overlap=50)
    final_chunks = splitter.split_documents(all_documents)
    
    # 2. Create the Vector Database with normalized embeddings + default L2
    print(f"🧠 Vectorizing {len(final_chunks)} chunks with all-mpnet-base-v2...")
    embeddings = _get_embeddings()
    print(f"Starting batch vectorization of {len(final_chunks)} chunks...")
    vector_db = FAISS.from_documents(final_chunks, embeddings)
    
    # 3. Save it
    vector_db.save_local(FAISS_DB_PATH)
    print(f"✅ Full Vector Vault created and saved to '{FAISS_DB_PATH}'!")
    return vector_db


if __name__ == "__main__":
    folder = "data" 
    
    vector_db = build_vector_store_from_folder(folder)
    
    if vector_db:
        # 4. Test Query
        user_question = "What are cognitive distortions?"
        results = search_knowledge(user_question, vector_db)
        
        print("\n--- 🎯 TOP SEARCH RESULT ---")
        if results:
            print(results[0])
        print("---------------------------")