import os
import re
import logging
from functools import lru_cache
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

FAISS_DB_PATH = "faiss_index"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

_embeddings = None
_vector_store = None
_vector_store_path: str | None = None


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
        chunk_size=500,
        chunk_overlap=80,
        length_function=len
    )
    
    chunks = splitter.split_text(raw)
    return chunks


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            show_progress=False,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_vector_store(path=None):
    """Load and cache the FAISS index globally — never reload per request."""
    global _vector_store, _vector_store_path
    load_path = path or FAISS_DB_PATH
    if _vector_store is not None and _vector_store_path == load_path:
        return _vector_store
    _vector_store = FAISS.load_local(
        load_path,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )
    _vector_store_path = load_path
    return _vector_store


def create_vector_store(documents):
    embeddings = get_embeddings()
    # Use default L2 — with normalized vectors, L2 and cosine rank identically
    # Score range becomes 0.0 (identical) to 2.0 (opposite), NOT 0–1
    vector_db = FAISS.from_documents(documents, embeddings)
    vector_db.save_local(FAISS_DB_PATH)
    global _vector_store, _vector_store_path
    _vector_store = vector_db
    _vector_store_path = FAISS_DB_PATH
    return vector_db

def load_vector_store(path=None):
    return get_vector_store(path)


def clean_query(query: str) -> list[str]:
    """
    Splits a comma-separated keyword string into individual search phrases.
    Returns a list of up to 3 cleaned phrase strings (no word truncation).
    Each phrase is lowercased and stripped. Empty phrases are discarded.
    """
    phrases = [p.strip().lower() for p in query.split(',') if p.strip()]
    return phrases[:3]  # Cap at 3 phrases to avoid over-querying


def _search_knowledge_uncached(phrases_tuple: tuple[str, ...], k: int, threshold: float):
    vector_store = get_vector_store()
    context_chunks = []
    seen = set()

    for phrase in phrases_tuple:
        results = vector_store.similarity_search_with_score(phrase, k=k)
        for doc, score in results:
            content = doc.page_content.strip()
            if content in seen:
                continue
            seen.add(content)
            if score <= threshold:
                source = doc.metadata.get("source", "Unknown Manual")
                context_chunks.append(f"[Source: {source}]\n{doc.page_content}")

    return tuple(context_chunks)


@lru_cache(maxsize=128)
def _search_knowledge_cached(phrases_tuple: tuple[str, ...], k: int, threshold: float):
    return _search_knowledge_uncached(phrases_tuple, k, threshold)


def search_knowledge(query, vector_store=None, k=5, threshold=1.15):
    """
    Searches the FAISS index using multi-phrase FAISS calls and unions results.
    vector_store arg kept for API compatibility; global cache is always used.
    """
    phrases = clean_query(query)
    if not phrases:
        return []
    phrases_tuple = tuple(phrases)
    cached = _search_knowledge_cached(phrases_tuple, k, threshold)
    return list(cached)

def load_all(folder_path="data"):
    print(f"Scanning folder: {folder_path}...")
    combined_text = ""
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            combined_text += extract_text(file_path) + "\n"
            
    return combined_text


def build_vector_store_from_folder(folder_path="data"):
    if not os.path.exists(folder_path):
        print(f"[ERROR] Error: Folder {folder_path} not found.")
        return None

    print(f"[INGESTION] Starting Full Ingestion from: {folder_path}")
    
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
                print(f"[WARNING] Warning: {filename} is empty or unreadable.")
    
    if not all_documents:
        print("❌ No valid text found in any PDFs. Check your data folder!")
        return None
        
    # 1. Split documents — micro-chunks preserve metadata automatically
    print(f"Chopping {len(all_documents)} documents into micro-chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    final_chunks = splitter.split_documents(all_documents)
    
    # 2. Create the Vector Database with normalized embeddings + default L2
    print(f"[VECTORIZATION] Vectorizing {len(final_chunks)} chunks with all-mpnet-base-v2...")
    print(f"Starting batch vectorization of {len(final_chunks)} chunks...")
    vector_db = create_vector_store(final_chunks)
    
    print(f"[SUCCESS] Full Vector Vault created and saved to '{FAISS_DB_PATH}'!")
    return vector_db

if __name__ == "__main__":

    print("Loading existing FAISS index...")

    vector_db = load_vector_store()

    user_question = input("\nEnter test query: ")

    results = search_knowledge(
        user_question,
        vector_db
    )

    print("\n--- 🎯 TOP SEARCH RESULT ---")

    if results:
        print(results[0])

    print("---------------------------")
