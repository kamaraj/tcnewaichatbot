import sys
import os
import asyncio
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app.services.pdf_processor import PDFProcessor
from app.services.vector_store import VectorStore

async def reindex():
    print("Initializing services...")
    pdf_processor = PDFProcessor()
    
    # Initialize VectorStore and CLEAR it
    vs = VectorStore()
    vs._documents = []
    vs._embeddings = None
    vs._save()
    print("Vector Store cleared.")
    
    upload_dir = Path("./uploads")
    files = list(upload_dir.glob("*.pdf"))
    
    if not files:
        print("No PDF files found in uploads/")
        return
        
    for file_path in files:
        print(f"Processing {file_path.name}...")
        try:
            # Process the PDF
            processed_doc = pdf_processor.process_pdf(str(file_path), file_path.name)
            
            # Index in vector store
            result = await vs.add_document_async(processed_doc)
            print(f"Indexed {result['chunks_indexed']} chunks.")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reindex())
