import os
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

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
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    chunks=splitter.split_text(raw)
    return chunks

def create_vector(chunks):
    print("Converting text into math (Vectorizing)... this might take a minute.")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store

def search_knowledge(query, vector_store):
    print(f"\n Searching for: '{query}'")
    
    results = vector_store.similarity_search(query, k=3)
    
    return [doc.page_content for doc in results]

def load_all(folder_path="data"):
    print(f"Scanning folder: {folder_path}...")
    combined_text = ""
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            combined_text += extract_text(file_path) + "\n"
            
    return combined_text

def create_vector_store(chunks):
    print("Converting text into math (Vectorizing)... this might take a minute.")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Create the vector database 
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store

def search_knowledge(query, vector_store):
    results = vector_store.similarity_search(query, k=3)
    
    return [doc.page_content for doc in results]

if __name__ == "__main__":
    test_file = "data/sample.pdf" 
    
    if os.path.exists(test_file):
        document_text = extract_text(test_file)
        document_chunks = split_chunks(document_text)
        
        # 1. Create the Vector Database
        vector_db = create_vector(document_chunks)
        print("✅ Vector Database created successfully!")
        
        # 2. Ask a question!
        user_question = "What are the core actions of psychological first aid?"
        
        # 3. Search the database
        answers = search_knowledge(user_question, vector_db)
        
        print("\n--- 🎯 TOP SEARCH RESULT ---")
        print(answers[0])
        print("---------------------------")
        
    else:
        print(f"❌ Error: Could not find {test_file}.")