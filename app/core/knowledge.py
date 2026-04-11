import os
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

def extract_text(file_path):
    print(f"Reading:{file_path}...")
    
    raw=''
    
    with open(file_path,'rb') as f:
        reader=PyPDF2.PdfReader(f)
        
        for page in reader.pages:
            extract=page.extract_text()
            if extract:
                raw+=extract+"\n"
                
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
    print("Chopping text into chunks...")
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    
    chunks=splitter.split_text(raw)
    return chunks

FAISS_DB_PATH = "faiss_index"

def create_vector_store(chunks):
    print("🧠 Converting text into math (Vectorizing)... this might take a minute.")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vector_store = FAISS.from_texts(chunks, embeddings)
    
    vector_store.save_local(FAISS_DB_PATH)
    print("Vector Vault permanently saved to disk!")
    
    return vector_store

def load_vector_store():
    print("Loading existing Vector Vault from disk...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    return FAISS.load_local(
        FAISS_DB_PATH, 
        embeddings, 
        allow_dangerous_deserialization=True,
        distance_strategy="COSINE" 
    )

def search_knowledge(query, vector_store, k=5, threshold=0.4):
    """
    Search with a strict threshold.
    lower score = higher similarity. 
    Matches above 0.8 are usually 'hallucinations' or irrelevant.
    """
    # 1. Get results with distance scores
    results = vector_store.similarity_search_with_score(query, k=k)
    
    context_chunks = []
    
    for doc, score in results:
        source = doc.metadata.get("source", "Unknown Manual")
        
        # --- THE FILTER ---
        if score <= threshold:
            # This is a 'Strong Match'
            formatted_chunk = f"[Source: {source}]\n{doc.page_content}"
            context_chunks.append(formatted_chunk)
            print(f"✅ VALID MATCH: {source} (Score: {score:.4f})")
        else:
            # This is 'Noise' - Skip it
            print(f"❌ REJECTED: {source} (Score: {score:.4f} is too weak)")

    # 2. Safety Fallback: If EVERYTHING was rejected, return an empty list
    # This prevents the AI from being forced to read irrelevant text.
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


if __name__ == "__main__":
    folder = "data" 
    
    if os.path.exists(folder):
        print(f"🚀 Starting Full Ingestion from: {folder}")
        
        all_documents = []
        for filename in os.listdir(folder):
            if filename.lower().endswith(".pdf"):
                path = os.path.join(folder, filename)
                
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
        else:
            # 1. Split documents (this preserves the metadata automatically)
            print(f"Chopping {len(all_documents)} documents into chunks...")
            splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
            final_chunks = splitter.split_documents(all_documents)
            
            # 2. Create the Vector Database
            print(f"🧠 Vectorizing {len(final_chunks)} chunks... (Wait for the Potato to finish)")
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            # Force Cosine Similarity
            vector_db = FAISS.from_documents(
                    final_chunks, 
                    embeddings, 
                    distance_strategy="COSINE"
            )
            
            # 3. Save it
            vector_db.save_local("faiss_index")
            print("✅ Full Vector Vault created and saved to 'faiss_index'!")
            
            # 4. Test Query
            user_question = "What are cognitive distortions?"
            results = search_knowledge(user_question, vector_db)
            
            print("\n--- 🎯 TOP SEARCH RESULT ---")
            if results:
                print(results[0])
            print("---------------------------")
    else:
        print(f"❌ Error: Folder {folder} not found.")