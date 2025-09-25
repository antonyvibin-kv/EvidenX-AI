import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
import os
from app.core.config import settings


class KnowledgeBase:
    def __init__(self):
        self.model = "models/text-embedding-004"
        self.qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = "evidenx"

    def get_text_embedding(self, data: str):
        """
        Convert input text into an embedding vector using Gemini text-embedding-004 model.

        Args:
            text (str): Input text to embed

        Returns:
            list: Embedding vector
        """
        genai.configure(api_key=settings.google_api_key)
        response = genai.embed_content(model=self.model, content=data)
        return response["embedding"]

    def insert_document(self, doc_id: int, data: str, metadata: dict = None):
        """Insert a text document and its embedding into Qdrant"""

        # Create a collection if it doesn't exist
        self.qdrant.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(
                size=768, distance="Cosine"
            ),  # 768 = Gemini embedding dimension
        )
        embedding = self.get_text_embedding(data)
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload={"text": data, **(metadata or {})},
                )
            ],
        )
        print(f"Inserted document {doc_id} into Qdrant.")

    def search_similar_documents(self, query: str, top_k: int = 5):
        """Search for similar documents in Qdrant based on a query string"""

        query_embedding = self.get_text_embedding(query)
        search_result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )
        text = search_result[0].payload.get("text")
        # print(
        #     f"Search results for query '{query}': {search_result[0].payload.get('text')}"
        # )
        return {"text": text}


# knowledge_base = KnowledgeBase()
# with open("app/storage/documents/fir.txt", "r") as f:
#     data = f.read()
#     print(data)
# knowledge_base.insert_document(1,data,{"source":"FIR"})
# print(knowledge_base.search_similar_documents("What is an FIR?", top_k=3))
