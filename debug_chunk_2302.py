import sys
import os
import json
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app.services.pdf_processor import PDFProcessor

def debug_chunking():
    processor = PDFProcessor()
    file_path = "uploads/IHSA Rulebook.pdf"
    
    print(f"Processing {file_path}...")
    doc = processor.process_pdf(file_path, "IHSA Rulebook.pdf")
    
    print(f"Total chunks: {len(doc.chunks)}")
    
    target_found = False
    for chunk in doc.chunks:
        if "2302" in chunk.text or "Regional President" in chunk.text:
            print(f"\n--- Chunk ID: {chunk.chunk_id} ---")
            print(f"Page: {chunk.metadata.get('page')}")
            print(f"Section ID: {chunk.metadata.get('section_id')}")
            print(f"Text Preview: {chunk.text[:200]}...")
            if "USHJA" in chunk.text:
                print(">>> CONTAINS 'USHJA'")
                target_found = True
            else:
                print(">>> DOES NOT CONTAIN 'USHJA'")
                
            print("-" * 20)

    if not target_found:
        print("CRITICAL: Rule 2302 with USHJA requirement NOT found in any chunk with '2302' or 'Regional President'.")

if __name__ == "__main__":
    debug_chunking()
