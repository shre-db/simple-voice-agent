from fastembed import TextEmbedding
from qdrant_client import QdrantClient

COLLECTION_NAME = "wise_faq"

# similarity threshold for FAQ match
SIMILARITY_THRESHOLD = 0.65

# Initialize embedding model
embedding_model = TextEmbedding()

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)


def query_faq(user_question: str):
    """
    Search the FAQ vector store and return the best match.
    """

    # Generate embedding for user query
    query_vector = list(embedding_model.embed([user_question]))[0]

    # Search Qdrant
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=1
    )

    if not results:
        return None

    best_match = results[0]

    score = best_match.score
    payload = best_match.payload

    # Check similarity threshold
    if score < SIMILARITY_THRESHOLD:
        return None

    return {
        "score": score,
        "id": payload["id"],
        "question": payload["question"],
        "answer": payload["answer"],
        "content": payload["content"],
        "source_url": payload["source_url"]
    }