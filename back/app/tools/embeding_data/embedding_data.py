# process_data.py
import json
# Main processing loop
processed_chunks = []
with open('chunk_output.jsonl', 'r') as f:
    for line in f:
        raw_item = json.loads(line)
        # print(raw_item)
        processed_chunks.append(raw_item)

# Now `processed_chunks` contains the final chunks ready for embedding.
# (in process_data.py)
from sentence_transformers import SentenceTransformer
import torch

print(f"Total chunks to embed: {len(processed_chunks)}")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
model = SentenceTransformer(
    'jinaai/jina-code-embeddings-1.5b', 
    trust_remote_code=True,
    device=device
)

# Instruction prefix for documents
print("Generating embeddings...")
doc_prefix = "Candidate code snippet:\n"

chunk_texts = [chunk['text'] for chunk in processed_chunks]
prefixed_texts = [doc_prefix + text for text in chunk_texts]

# Generate embeddings in batches for efficiency
print("Encoding texts...")
embeddings = model.encode(prefixed_texts, batch_size=8, show_progress_bar=True)

for i, chunk in enumerate(processed_chunks):
    chunk['embedding'] = embeddings[i].tolist()

print("Embeddings generated and added to chunks.")

# --- ステップ3: 最終的なデータをファイルに保存 ---
output_filepath = "embedded_chunks.jsonl"
print(f"\nステップ3: 埋め込みを含むチャンクを'{output_filepath}'に保存中...")

with open(output_filepath, 'w', encoding='utf-8') as f_out:
    for chunk in processed_chunks:
        # 各チャンク（辞書）をJSON文字列に変換してファイルに書き込む
        f_out.write(json.dumps(chunk, ensure_ascii=False) + '\n')

print(f"全ての処理が完了しました。'{output_filepath}' が作成されました。")
