python - <<EOF
from fastembed import TextEmbedding
embedding_model = TextEmbedding()
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
query = "why is my transfer late"

query_vector = list(embedding_model.embed([query]))[0]

results = client.query_points(
    collection_name="wise_faq",
    query=query_vector,
    limit=1
)

print(results.points[0].payload["question"])
EOF