# query_manim_docs.py

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

persist_dir = "./manim_chroma_db"

embedding_function = HuggingFaceEmbeddings(model_name="jinaai/jina-code-embeddings-1.5b")

db = Chroma(
    collection_name="manim_docs",
    persist_directory=persist_dir,
    embedding_function=embedding_function,
)

query = "Manimでシーンにオブジェクトを追加するアニメーションは？"
results = db.similarity_search(query, k=3)

for i, r in enumerate(results):
    print(f"--- Result {i+1} ---")
    print("Source:", r.metadata.get("source_url", "N/A"))
    print("Full Name:", r.metadata.get("full_name", "N/A"))
    print("Snippet:", r.page_content[:200], "...\n")
