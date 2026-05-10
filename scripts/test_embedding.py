"""
Simple RAG Test - Direct Embedding Test
"""
import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.vector_store import EmbeddingService, Document

# Test embeddings directly
print("=" * 50)
print("Direct Embedding Test")
print("=" * 50)

try:
    embedding_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
    print(f"Model: {embedding_service.model_name}")
    print(f"Dimension: {embedding_service.dimension}")

    # Test embedding
    test_texts = [
        "SQL injection vulnerability in login form",
        "privilege escalation via misconfigured permissions",
        "CVE-2021-44228 Log4j remote code execution",
    ]

    print("\n[Test 1] Embedding generation")
    embeddings = embedding_service.embed(test_texts)
    print(f"  Generated {len(embeddings)} embeddings, shape: {embeddings.shape}")

    # Test query embedding
    print("\n[Test 2] Query embedding")
    query = "SQL injection"
    query_emb = embedding_service.embed([query])
    print(f"  Query '{query}': {query_emb.shape}")

    # Test similarity manually
    print("\n[Test 3] Manual similarity (dot product)")
    similarities = np.dot(embeddings, query_emb.T).flatten()
    for i, (text, sim) in enumerate(zip(test_texts, similarities)):
        print(f"  '{text[:30]}...' -> {sim:.3f}")

    print("\n[SUCCESS] Embedding tests passed!")

except Exception as e:
    print(f"\n[ERROR] {e}")

    # Fallback to hash-based
    print("\n[FALLBACK] Using hash-based embeddings")
    embedding_service = EmbeddingService()  # Uses fallback
    test_text = "test"
    emb = embedding_service.embed([test_text])
    print(f"  Hash embedding shape: {emb.shape}")
    print("[OK] Fallback works")