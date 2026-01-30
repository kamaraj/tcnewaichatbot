"""
PDF Processing Service.
Handles text extraction, cleaning, and chunking of PDF documents.
"""

import os
import re
import hashlib
import pypdf
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
        # Default settings if not provided
        chunk_size = getattr(settings, "chunk_size", 1000)
        chunk_overlap = getattr(settings, "chunk_overlap", 200)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF with page-level metadata using pypdf.
        """
        pages = []
        
        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    
                    if text:
                        # Clean the text
                        text = self._clean_text(text)
                        
                        if text.strip():
                            pages.append({
                                "text": text,
                                "page": page_num
                            })
        
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")
        
        return pages
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip very short lines that might be page numbers
            if len(line) < 4 and line.replace('.', '').isdigit():
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def process_pdf(self, file_path: str, filename: str) -> ProcessedDocument:
        """
        Process a PDF file into chunks for indexing based on rule boundaries.
        Implements Step 1.1: Chunk by Rule/Section boundaries.
        """
        # Generate document ID from content hash
        with open(file_path, 'rb') as f:
            doc_id = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Extract text by page
        pages = self.extract_text_from_pdf(file_path)
        
        if not pages:
            raise ValueError("No text could be extracted from the PDF")
        
        chunks = []
        active_section = None
        active_subrule = None
        active_section_full = None

        # Pattern for finding sections/rules like "Section 7207" or "Rule 1102.A"
        section_pattern = re.compile(r'(?:^|\n)\s*(?:(?:Section|Rule|Article)\s+)?(\d{3,4})(?:\.([A-Z0-9]+))?', re.IGNORECASE)

        for page_data in pages:
            page_num = page_data["page"]
            page_text = page_data["text"]
            
            # Split by section boundaries
            matches = list(section_pattern.finditer(page_text))
            
            # If no sections found on this page, continue using active_section
            if not matches:
                paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                for i, para in enumerate(paragraphs):
                    chunk_meta = self._extract_rich_metadata(para)
                    # If current paragraph doesn't have a section but we have an active one, use it
                    if not chunk_meta["section_id"] and active_section:
                        chunk_meta["section_id"] = active_section
                        chunk_meta["subrule"] = active_subrule
                        chunk_meta["section_full"] = active_section_full
                    
                    self._add_chunk_with_precomputed_meta(chunks, para, page_num, doc_id, filename, i, chunk_meta)
                continue

            # Process split points
            split_points = []
            for m in matches:
                # Basic context check: is it a header or just a mention?
                start = m.start()
                prefix = page_text[max(0, start-10):start].lower()
                # If "see rule" or "in section", skip as header
                if 'see' in prefix or 'refer' in prefix or '(' in prefix:
                    continue
                split_points.append(m)

            if not split_points:
                # All matches were references, treat page as paragraphs
                paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                for i, para in enumerate(paragraphs):
                    chunk_meta = self._extract_rich_metadata(para)
                    if not chunk_meta["section_id"] and active_section:
                        chunk_meta["section_id"] = active_section
                        chunk_meta["subrule"] = active_subrule
                        chunk_meta["section_full"] = active_section_full
                    self._add_chunk_with_precomputed_meta(chunks, para, page_num, doc_id, filename, i, chunk_meta)
                continue

            # Add pseudo-split at 0 if first split is not at 0
            current_idx = 0
            for i, match in enumerate(split_points):
                start = match.start()
                end = split_points[i+1].start() if i+1 < len(split_points) else len(page_text)
                
                # Text before the first rule on the page
                if i == 0 and start > 0:
                    pre_text = page_text[0:start].strip()
                    if pre_text:
                        chunk_meta = self._extract_rich_metadata(pre_text)
                        if not chunk_meta["section_id"] and active_section:
                            chunk_meta["section_id"] = active_section
                            chunk_meta["subrule"] = active_subrule
                            chunk_meta["section_full"] = active_section_full
                        self._add_chunk_with_precomputed_meta(chunks, pre_text, page_num, doc_id, filename, 0, chunk_meta)

                # The rule itself
                rule_text = page_text[start:end].strip()
                if rule_text:
                    chunk_meta = self._extract_rich_metadata(rule_text)
                    # Update active state if we found a new section
                    if chunk_meta["section_id"]:
                        active_section = chunk_meta["section_id"]
                        active_subrule = chunk_meta["subrule"]
                        active_section_full = chunk_meta["section_full"]
                    elif active_section:
                        chunk_meta["section_id"] = active_section
                        chunk_meta["subrule"] = active_subrule
                        chunk_meta["section_full"] = active_section_full
                        
                    self._add_chunk_with_precomputed_meta(chunks, rule_text, page_num, doc_id, filename, i + 1, chunk_meta)
        
        return ProcessedDocument(
            doc_id=doc_id,
            filename=filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            chunks=chunks
        )

    def _add_chunk_with_precomputed_meta(self, chunks: List[DocumentChunk], text: str, page_num: int, doc_id: str, filename: str, index: int, meta: Dict[str, Any]):
        """Add chunk with already computed metadata."""
        chunk_id = f"{doc_id}_p{page_num}_s{meta.get('section_id', 'none')}_c{index}"
        
        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "page": page_num,
            "chunk_index": index,
            "source": f"{filename} (Page {page_num})"
        }
        metadata.update(meta)
            
        chunks.append(DocumentChunk(
            text=text,
            metadata=metadata,
            chunk_id=chunk_id
        ))

    def _add_chunk_with_meta(self, chunks: List[DocumentChunk], text: str, page_num: int, doc_id: str, filename: str, index: int):
        """Extract rich metadata and add chunk."""
        meta = self._extract_rich_metadata(text)
        chunk_id = f"{doc_id}_p{page_num}_s{meta.get('section_id', 'none')}_c{index}"
        
        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "page": page_num,
            "chunk_index": index,
            "source": f"{filename} (Page {page_num})"
        }
        metadata.update(meta)
            
        chunks.append(DocumentChunk(
            text=text,
            metadata=metadata,
            chunk_id=chunk_id
        ))

    def _extract_rich_metadata(self, text: str) -> Dict[str, Any]:
        """Implement Step 1.2: Rich metadata extraction."""
        meta = {
            "section_id": None,
            "subrule": None,
            "section_full": None,
            "subject_role": "general",
            "topic_tags": []
        }
        
        # 1. Section/Subrule Extraction
        section_match = re.search(r'(?:Section|Rule|Article)?\s*(\d{3,4})(?:\.([A-Z0-9]+))?', text[:100], re.IGNORECASE)
        if section_match:
            meta["section_id"] = int(section_match.group(1))
            meta["subrule"] = section_match.group(2)
            meta["section_full"] = f"{section_match.group(1)}{'.' + section_match.group(2) if section_match.group(2) else ''}"
        
        # 2. Subject Role (Heuristic)
        role_keywords = {
            "coach": ["coach", "coaches", "trainer"],
            "rider": ["rider", "student", "undergraduate"],
            "steward": ["steward", "official", "judge"],
            "exhibitor": ["exhibitor", "handler"],
            "horse": ["horse", "pony", "equine", "animal"],
            "handler": ["handler", "groom"]
        }
        
        lower_text = text.lower()
        for role, keywords in role_keywords.items():
            if any(f" {k}" in lower_text or lower_text.startswith(k) for k in keywords):
                meta["subject_role"] = role
                break
        
        # 3. Topic Tags
        topic_map = {
            "regionals": ["regional", "zones", "nationals", "semi-finals"],
            "points": ["points", "acquire", "accumulate", "total"],
            "eligibility": ["eligible", "eligibility", "membership", "requirements"],
            "turnout": ["attire", "clothing", "boots", "breeches", "hats"],
            "equipment": ["tack", "saddle", "bridle", "martingale", "whip", "spurs"],
            "timing": ["minutes", "seconds", "weeks", "days", "time limit"]
        }
        
        for topic, keywords in topic_map.items():
            if any(k in lower_text for k in keywords):
                meta["topic_tags"].append(topic)
                
        return meta

    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Save uploaded file to disk."""
        safe_filename = self._safe_filename(filename)
        file_path = os.path.join(settings.upload_dir, safe_filename)
        
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
        filename = os.path.basename(filename)
        for char in ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']:
            filename = filename.replace(char, '_')
        return filename
