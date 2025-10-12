import json
from langchain_community.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# --- Step 1: Load JSONL ---
input_path = "embedded_data.jsonl"
texts, metadatas, embeddings = [], [], []

with open(input_path, "r", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        texts.append(d["text"])
        metadatas.append(d.get("metadata", {}))
        embeddings.append(d["embedding"])

print(f"✅ Loaded {len(texts)} chunks from {input_path}")

# --- Step 2: Initialize embedding model ---
embedding_fn = HuggingFaceEmbeddings(model_name="jinaai/jina-code-embeddings-1.5b")

# --- Step 3: Create empty Chroma DB ---
persist_dir = "./manim_chroma_db"
db = Chroma(
    collection_name="manim_docs",
    embedding_function=embedding_fn,
    persist_directory=persist_dir,
)

# --- Step 4: Insert existing embeddings manually ---
# Chroma APIは add_embeddings() を使う
ids = [f"chunk_{i}" for i in range(len(texts))]
db._collection.add(
    embeddings=embeddings,
    documents=texts,
    metadatas=metadatas,
    ids=ids,
)

# --- Step 5: Persist ---
db.persist()
print(f"✅ Successfully built vector DB with {len(texts)} documents in {persist_dir}")
