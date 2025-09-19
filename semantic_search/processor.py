# semantic_search/processor.py

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any]
    chunk_index: int
    total_chunks: int

class DocumentProcessor:
    """
    Processes legal documents for semantic search.
    Handles chunking, cleaning, and metadata extraction.
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        logger.info(f"Initialized DocumentProcessor (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def process_document(self, 
                        document_id: str,
                        text: str,
                        metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        """
        Process a single document into chunks.
        
        Args:
            document_id: Unique document identifier
            text: Document text content
            metadata: Optional document metadata
            
        Returns:
            List of document chunks
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            logger.warning(f"Document {document_id} too short to process")
            return []
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract metadata from text if not provided
        if metadata is None:
            metadata = {}
        
        # Add extracted metadata
        extracted_metadata = self._extract_metadata(cleaned_text)
        metadata.update(extracted_metadata)
        
        # Create chunks
        chunks = self._create_chunks(cleaned_text)
        
        # Create DocumentChunk objects
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = self._generate_chunk_id(document_id, i)
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                text=chunk_text,
                metadata={
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                },
                chunk_index=i,
                total_chunks=len(chunks)
            )
            document_chunks.append(chunk)
        
        logger.info(f"Processed document {document_id} into {len(chunks)} chunks")
        return document_chunks
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for processing.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Turkish characters
        # Keep: letters, numbers, spaces, and common punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\"\'ÇĞIİÖŞÜçğıiöşü]', ' ', text)
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Trim
        text = text.strip()
        
        return text
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from legal document text.
        
        Args:
            text: Document text
            
        Returns:
            Extracted metadata
        """
        metadata = {}
        
        # Extract case numbers (Esas/Karar)
        esas_pattern = r'E(?:sas)?[\s\.\:]*(\d{4})[\/\-](\d+)'
        karar_pattern = r'K(?:arar)?[\s\.\:]*(\d{4})[\/\-](\d+)'
        
        esas_match = re.search(esas_pattern, text[:500])  # Look in first 500 chars
        if esas_match:
            metadata['esas_no'] = f"E.{esas_match.group(1)}/{esas_match.group(2)}"
        
        karar_match = re.search(karar_pattern, text[:500])
        if karar_match:
            metadata['karar_no'] = f"K.{karar_match.group(1)}/{karar_match.group(2)}"
        
        # Extract dates (DD.MM.YYYY or DD/MM/YYYY format)
        date_pattern = r'(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{4})'
        dates = re.findall(date_pattern, text[:1000])  # Look in first 1000 chars
        if dates:
            # Take the first date as decision date
            day, month, year = dates[0]
            metadata['karar_tarihi'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Extract court/chamber name
        chamber_patterns = [
            r'(\d+)\.\s*Hukuk\s+Dairesi',
            r'(\d+)\.\s*Ceza\s+Dairesi',
            r'Hukuk\s+Genel\s+Kurulu',
            r'Ceza\s+Genel\s+Kurulu',
            r'(\d+)\.\s*Daire'
        ]
        
        for pattern in chamber_patterns:
            match = re.search(pattern, text[:500], re.IGNORECASE)
            if match:
                metadata['chamber'] = match.group(0)
                break
        
        return metadata
    
    def _create_chunks(self, text: str) -> List[str]:
        """
        Create overlapping chunks from text.
        
        Args:
            text: Cleaned document text
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # Split by sentences for better semantic coherence
        sentences = self._split_sentences(text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Create overlap for next chunk
                overlap_size = 0
                overlap_sentences = []
                
                # Add sentences from the end until we reach overlap size
                for sent in reversed(current_chunk):
                    overlap_size += len(sent)
                    overlap_sentences.insert(0, sent)
                    if overlap_size >= self.chunk_overlap:
                        break
                
                # Start new chunk with overlap
                current_chunk = overlap_sentences
                current_size = sum(len(s) for s in current_chunk)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add final chunk if not empty
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting for Turkish text
        # Split on period, question mark, exclamation, but not on abbreviations
        
        # Common Turkish abbreviations to preserve
        abbreviations = ['Dr', 'Prof', 'Av', 'Md', 'Yrd', 'Doç', 'No', 'S', 'vs', 'vb', 'bkz']
        
        # Replace abbreviations temporarily
        temp_text = text
        replacements = {}
        for i, abbr in enumerate(abbreviations):
            placeholder = f"__ABBR{i}__"
            temp_text = temp_text.replace(f"{abbr}.", placeholder)
            replacements[placeholder] = f"{abbr}."
        
        # Split sentences
        sentence_endings = re.compile(r'[.!?]+')
        sentences = sentence_endings.split(temp_text)
        
        # Restore abbreviations and clean
        cleaned_sentences = []
        for sentence in sentences:
            # Restore abbreviations
            for placeholder, original in replacements.items():
                sentence = sentence.replace(placeholder, original)
            
            # Clean and add if not empty
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Minimum sentence length
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """
        Generate unique chunk ID.
        
        Args:
            document_id: Parent document ID
            chunk_index: Index of chunk in document
            
        Returns:
            Unique chunk ID
        """
        chunk_string = f"{document_id}_chunk_{chunk_index}"
        chunk_hash = hashlib.md5(chunk_string.encode()).hexdigest()[:8]
        return f"{document_id}_c{chunk_index}_{chunk_hash}"
    
    def combine_chunks(self, chunks: List[DocumentChunk]) -> str:
        """
        Combine chunks back into full document text.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Combined text
        """
        if not chunks:
            return ""
        
        # Sort by chunk index
        sorted_chunks = sorted(chunks, key=lambda x: x.chunk_index)
        
        # For overlapping chunks, we need to be careful about duplication
        # Simple approach: just concatenate with space
        combined = " ".join([chunk.text for chunk in sorted_chunks])
        
        return combined