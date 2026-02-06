"""
RAG (Retrieval Augmented Generation) service for MSME ODR chatbot.
Handles PDF parsing, text chunking, embeddings, and similarity search.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

# PDF parsing
from pypdf import PdfReader

# Embeddings
from sentence_transformers import SentenceTransformer

# Vector store
import faiss


class RAGService:
    """Service for RAG-based document retrieval."""

    # Paths
    KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
    VECTOR_DB_DIR = Path(__file__).parent.parent.parent / "data" / "vector_db"
    INDEX_PATH = VECTOR_DB_DIR / "faiss_index.bin"
    METADATA_PATH = VECTOR_DB_DIR / "chunks_metadata.json"

    # Chunking config
    CHUNK_SIZE = 500  # characters
    CHUNK_OVERLAP = 50  # characters

    # Retrieval config
    TOP_K = 4  # number of chunks to retrieve

    # Embedding model (lightweight, good quality)
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(self):
        """Initialize RAG service with embedding model and load index if exists."""
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatL2] = None
        self.chunks_metadata: List[Dict] = []
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy load the model and index."""
        if self._loaded:
            return

        # Load embedding model
        self.model = SentenceTransformer(self.EMBEDDING_MODEL)

        # Load index if exists
        if self.INDEX_PATH.exists() and self.METADATA_PATH.exists():
            self.index = faiss.read_index(str(self.INDEX_PATH))
            with open(self.METADATA_PATH, "r", encoding="utf-8") as f:
                self.chunks_metadata = json.load(f)

        self._loaded = True

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from a PDF file."""
        reader = PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n".join(text_parts)

    def chunk_text(self, text: str, source: str) -> List[Dict]:
        """
        Split text into overlapping chunks.

        Args:
            text: The text to chunk
            source: Source filename for metadata

        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Clean text
        text = text.replace("\n", " ").replace("\r", " ")
        text = " ".join(text.split())  # normalize whitespace

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending near the chunk boundary
                for sep in [". ", "? ", "! ", "; "]:
                    last_sep = text.rfind(sep, start + self.CHUNK_SIZE // 2, end + 50)
                    if last_sep != -1:
                        end = last_sep + 1
                        break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "start_char": start,
                    "end_char": end
                })

            # Move start with overlap
            start = end - self.CHUNK_OVERLAP
            if start >= len(text) - self.CHUNK_OVERLAP:
                break

        return chunks

    def build_index(self, force_rebuild: bool = False) -> Dict:
        """
        Build FAISS index from all PDFs in knowledge_base directory.

        Args:
            force_rebuild: If True, rebuild even if index exists

        Returns:
            Dictionary with build statistics
        """
        # Ensure directories exist
        self.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

        # Check if rebuild needed
        if not force_rebuild and self.INDEX_PATH.exists():
            return {"status": "skipped", "message": "Index already exists. Use force_rebuild=True to rebuild."}

        # Load model
        if self.model is None:
            self.model = SentenceTransformer(self.EMBEDDING_MODEL)

        # Find all PDFs
        pdf_files = list(self.KNOWLEDGE_BASE_DIR.glob("*.pdf"))
        if not pdf_files:
            return {"status": "error", "message": f"No PDF files found in {self.KNOWLEDGE_BASE_DIR}"}

        all_chunks = []
        stats = {"files_processed": 0, "total_chunks": 0, "files": []}

        # Process each PDF
        for pdf_path in pdf_files:
            print(f"Processing: {pdf_path.name}")

            try:
                # Extract text
                text = self.extract_text_from_pdf(pdf_path)

                # Chunk text
                chunks = self.chunk_text(text, pdf_path.name)
                all_chunks.extend(chunks)

                stats["files"].append({
                    "name": pdf_path.name,
                    "chunks": len(chunks),
                    "characters": len(text)
                })
                stats["files_processed"] += 1

            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
                stats["files"].append({
                    "name": pdf_path.name,
                    "error": str(e)
                })

        if not all_chunks:
            return {"status": "error", "message": "No chunks extracted from PDFs"}

        # Generate embeddings
        print(f"Generating embeddings for {len(all_chunks)} chunks...")
        chunk_texts = [c["text"] for c in all_chunks]
        embeddings = self.model.encode(chunk_texts, show_progress_bar=True)

        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype(np.float32))

        # Save index
        faiss.write_index(self.index, str(self.INDEX_PATH))

        # Save metadata
        self.chunks_metadata = all_chunks
        with open(self.METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        stats["total_chunks"] = len(all_chunks)
        stats["embedding_dimension"] = dimension
        stats["status"] = "success"

        self._loaded = True

        return stats

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Search for relevant chunks given a query.

        Args:
            query: User's query text
            top_k: Number of results to return (default: self.TOP_K)

        Returns:
            List of relevant chunks with scores
        """
        self._ensure_loaded()

        if self.index is None or not self.chunks_metadata:
            return []

        if top_k is None:
            top_k = self.TOP_K

        # Generate query embedding
        query_embedding = self.model.encode([query])

        # Search FAISS index
        distances, indices = self.index.search(
            query_embedding.astype(np.float32),
            min(top_k, len(self.chunks_metadata))
        )

        # Build results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunks_metadata):
                chunk = self.chunks_metadata[idx].copy()
                chunk["score"] = float(distances[0][i])
                results.append(chunk)

        return results

    def get_context_for_query(self, query: str, top_k: Optional[int] = None) -> str:
        """
        Get formatted context string for LLM prompt injection.

        Args:
            query: User's query
            top_k: Number of chunks to retrieve

        Returns:
            Formatted context string ready for prompt injection
        """
        results = self.search(query, top_k)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source: {result['source']}]\n{result['text']}")

        return "\n\n---\n\n".join(context_parts)

    def is_index_available(self) -> bool:
        """Check if the FAISS index is available."""
        return self.INDEX_PATH.exists() and self.METADATA_PATH.exists()


# Singleton instance for reuse
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
