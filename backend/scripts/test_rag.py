#!/usr/bin/env python3
"""
Quick test script to verify RAG retrieval is working.
Run from backend directory: python -m scripts.test_rag
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.rag_service import get_rag_service


def test_rag():
    rag = get_rag_service()

    print("=== RAG System Test ===\n")
    print(f"Index available: {rag.is_index_available()}")

    if not rag.is_index_available():
        print("ERROR: Index not found. Run 'python -m scripts.build_index' first.")
        return

    # Test queries
    test_queries = [
        "What is Section 15 about delayed payments?",
        "What is the interest rate for delayed payments?",
        "How do I file a dispute with Facilitation Council?",
        "What is the definition of micro enterprise?",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print(f"{'='*60}")

        results = rag.search(query, top_k=2)

        if results:
            for i, r in enumerate(results, 1):
                print(f"\n--- Result {i} (score: {r['score']:.4f}) ---")
                print(f"Source: {r['source']}")
                print(f"Text: {r['text'][:300]}...")
        else:
            print("No results found!")

    # Show formatted context (what gets injected into LLM)
    print(f"\n\n{'='*60}")
    print("FORMATTED CONTEXT FOR LLM (sample query):")
    print(f"{'='*60}")
    context = rag.get_context_for_query("delayed payment interest rate")
    print(context[:1500] if context else "No context retrieved")


if __name__ == "__main__":
    test_rag()
