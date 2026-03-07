import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from fastembed import TextEmbedding

COLLECTION_NAME = "wise_faq"

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# Initialize embedding model
embedding_model = TextEmbedding()

# Load dataset
data_path = Path(__file__).resolve().parent.parent / "data" / "wise_faq.json"

with open(data_path, "r") as f:
    faqs = json.load(f)

print(f"Loaded {len(faqs)} FAQ articles")

# Generate embeddings
texts_to_embed = [
    f"{faq['question']} {' '.join(faq['keywords'])}"
    for faq in faqs
]

embeddings = list(embedding_model.embed(texts_to_embed))

vector_size = len(embeddings[0])

# Create collection
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=vector_size,
        distance=Distance.COSINE
    )
)

print("Collection created")

# Prepare points
points = []

for idx, (faq, vector) in enumerate(zip(faqs, embeddings)):
    payload = {
        "id": faq["id"],
        "question": faq["question"],
        "answer": faq["answer"],
        "content": faq["content"],
        "source_url": faq["source_url"]
    }

    points.append(
        PointStruct(
            id=idx,
            vector=vector,
            payload=payload
        )
    )

# Upload to Qdrant
client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)

print("FAQ data successfully ingested into Qdrant")