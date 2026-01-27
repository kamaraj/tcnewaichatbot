"""
PDF Processing Service.
Handles text extraction, cleaning, and chunking of PDF documents.
"""

import os
import hashlib
import fitz  # PyMuPDF
from typing import List, Dict, Any
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..config import settings


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document."""
    text: str
    metadata: Dict[str, Any]
    chunk_id: str


@dataclass
class ProcessedDocument:
    """Represents a fully processed document."""
    doc_id: str
    filename: str
    total_pages: int
    total_chunks: int
    chunks: List[DocumentChunk]


class PDFProcessor:
    """Process PDF files for RAG pipeline."""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF with page-level metadata.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of dicts with 'text' and 'page' keys
        """
        pages = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                
                # Clean the text
                text = self._clean_text(text)
                
                if text.strip():
                    pages.append({
                        "text": text,
                        "page": page_num
                    })
            
            doc.close()
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")
        
        return pages
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Normalize whitespace
        text = " ".join(text.split())
        
        # Remove common header/footer patterns (can be customized)
        # This is a basic implementation
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip very short lines that might be page numbers
            if len(line.strip()) < 3 and line.strip().isdigit():
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def process_pdf(self, file_path: str, filename: str) -> ProcessedDocument:
        """
        Process a PDF file into chunks for indexing.
        
        Args:
            file_path: Path to the PDF file
            filename: Original filename
            
        Returns:
            ProcessedDocument with chunks and metadata
        """
        # Generate document ID from content hash
        with open(file_path, 'rb') as f:
            doc_id = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Extract text by page
        pages = self.extract_text_from_pdf(file_path)
        
        if not pages:
            raise ValueError("No text could be extracted from the PDF")
        
        # Combine all text while tracking page boundaries
        chunks = []
        
        for page_data in pages:
            page_num = page_data["page"]
            page_text = page_data["text"]
            
            # Split page text into chunks
            page_chunks = self.text_splitter.split_text(page_text)
            
            for i, chunk_text in enumerate(page_chunks):
                chunk_id = f"{doc_id}_p{page_num}_c{i}"
                
                chunk = DocumentChunk(
                    text=chunk_text,
                    metadata={
                        "doc_id": doc_id,
                        "filename": filename,
                        "page": page_num,
                        "chunk_index": i,
                        "source": f"{filename} (Page {page_num})"
                    },
                    chunk_id=chunk_id
                )
                chunks.append(chunk)
        
        return ProcessedDocument(
            doc_id=doc_id,
            filename=filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            chunks=chunks
        )
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        # Generate safe filename
        safe_filename = self._safe_filename(filename)
        file_path = os.path.join(settings.upload_dir, safe_filename)
        
        # Handle duplicate filenames
        counter = 1
        base, ext = os.path.splitext(file_path)
        while os.path.exists(file_path):
            file_path = f"{base}_{counter}{ext}"
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
    
    def _safe_filename(self, filename: str) -> str:
        """Create a safe filename."""
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Replace problematic characters
        for char in ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']:
            filename = filename.replace(char, '_')
        
        return filename
