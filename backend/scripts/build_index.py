#!/usr/bin/env python3
"""
Script to build/rebuild the FAISS vector index from PDF documents.

Usage:
    python -m scripts.build_index           # Build if not exists
    python -m scripts.build_index --force   # Force rebuild
    python -m scripts.build_index --info    # Show index info

Run from the backend directory:
    cd backend
    python -m scripts.build_index
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.rag_service import RAGService


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS vector index from knowledge base PDFs"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force rebuild even if index exists"
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show index info without building"
    )

    args = parser.parse_args()

    rag_service = RAGService()

    # Info mode
    if args.info:
        print("\n=== RAG Index Information ===\n")
        print(f"Knowledge Base: {rag_service.KNOWLEDGE_BASE_DIR}")
        print(f"Vector DB: {rag_service.VECTOR_DB_DIR}")
        print(f"Index exists: {rag_service.INDEX_PATH.exists()}")
        print(f"Metadata exists: {rag_service.METADATA_PATH.exists()}")

        # List PDFs
        pdfs = list(rag_service.KNOWLEDGE_BASE_DIR.glob("*.pdf"))
        print(f"\nPDF files in knowledge base: {len(pdfs)}")
        for pdf in pdfs:
            size_kb = pdf.stat().st_size / 1024
            print(f"  - {pdf.name} ({size_kb:.1f} KB)")

        # Show chunk count if metadata exists
        if rag_service.METADATA_PATH.exists():
            import json
            with open(rag_service.METADATA_PATH) as f:
                chunks = json.load(f)
            print(f"\nIndexed chunks: {len(chunks)}")

            # Group by source
            sources = {}
            for chunk in chunks:
                src = chunk.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1
            print("Chunks per source:")
            for src, count in sources.items():
                print(f"  - {src}: {count} chunks")

        return

    # Build mode
    print("\n=== Building RAG Index ===\n")
    print(f"Knowledge Base: {rag_service.KNOWLEDGE_BASE_DIR}")
    print(f"Vector DB: {rag_service.VECTOR_DB_DIR}")
    print(f"Embedding Model: {rag_service.EMBEDDING_MODEL}")
    print(f"Chunk Size: {rag_service.CHUNK_SIZE} chars (overlap: {rag_service.CHUNK_OVERLAP})")
    print()

    result = rag_service.build_index(force_rebuild=args.force)

    if result["status"] == "success":
        print("\n=== Build Complete ===\n")
        print(f"Files processed: {result['files_processed']}")
        print(f"Total chunks: {result['total_chunks']}")
        print(f"Embedding dimension: {result['embedding_dimension']}")
        print("\nPer-file details:")
        for file_info in result["files"]:
            if "error" in file_info:
                print(f"  - {file_info['name']}: ERROR - {file_info['error']}")
            else:
                print(f"  - {file_info['name']}: {file_info['chunks']} chunks ({file_info['characters']} chars)")
        print(f"\nIndex saved to: {rag_service.INDEX_PATH}")
        print(f"Metadata saved to: {rag_service.METADATA_PATH}")

    elif result["status"] == "skipped":
        print(result["message"])
        print("Use --force to rebuild.")

    else:
        print(f"Error: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
