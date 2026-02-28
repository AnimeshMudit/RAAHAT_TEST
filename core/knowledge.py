import os
from pypdf import PdfReader

data=r"C:\Users\Animesh\Documents\Projects\RAAHAT_TAHAAR\data"

def extract_from_pdf(file_path):
    """Reads a PDF and returns all its text as a single string."""
    with open(file_path,"rb") as f:
        file=PdfReader(f)

        full_page=""
        
        for page in file.pages:
            page_text=page.extract_text()
            
            if page_text:
                full_page+=page_text+"\n"
                
    return full_page

def chunk_text(text,chunk_size=1000):
    chunks=[]
    
    for i in range(0,len(text),chunk_size):
        chunk=text[i:i+chunk_size]
        chunks.append(chunk)

    return chunks
    
if __name__=="__main__":
    sample = os.path.join(data, "Grounding-Exercise.pdf")
    
    # 1. Extract the giant string
    text = extract_from_pdf(sample)
    
    # 2. Chop it up into chunks of 500 characters
    text_chunks = chunk_text(text, chunk_size=500)
    
    print(f"Total chunks created: {len(text_chunks)}")
    print("--- CHUNK #1 ---")
    print(text_chunks[0])
    print("--- CHUNK #2 ---")
    print(text_chunks[1])