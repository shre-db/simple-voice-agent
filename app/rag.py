import os
from functools import lru_cache

from fastembed import TextEmbedding
from qdrant_client import QdrantClient

COLLECTION_NAME = "wise_faq"

# similarity threshold for FAQ match
SIMILARITY_THRESHOLD = 0.65

qdrant_host = os.getenv("QDRANT_HOST", "localhost")
qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    return TextEmbedding()


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=qdrant_host, port=qdrant_port)


def query_faq(user_question: str):
    """
    Search the FAQ vector store and return the best match.
    """

    try:
        embedding_model = get_embedding_model()
        client = get_qdrant_client()

        # Generate embedding for user query
        query_vector = list(embedding_model.embed([user_question]))[0]

        # Search Qdrant
        query_response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=1,
        )
        results = query_response.points
    except Exception as exc:
        print(f"RAG lookup failed: {exc}")
        return None

    if not results:
        return None

    best_match = results[0]

    score = best_match.score
    payload = best_match.payload or {}

    # Check similarity threshold
    if score < SIMILARITY_THRESHOLD:
        return None

    return {
        "score": score,
        "id": payload.get("id"),
        "question": payload.get("question"),
        "answer": payload.get("answer"),
        "content": payload.get("content", ""),
        "source_url": payload.get("source_url")
    }
