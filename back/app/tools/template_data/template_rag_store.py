from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import uuid
import math
import numpy as np

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class TemplateRAGStore:
    """
    Chroma ベクトルストアを介してテンプレート要約を永続化・検索するヘルパー。
    """

    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parent # back/app/tools/template_data
        self.persist_dir = base_dir / "template_chroma_db"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.collection_name = "template_summaries"
        self.embedding_model = "cl-nagoya/ruri-v3-30m"

        self._embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )

        self._vector_store = Chroma(
            collection_name=self.collection_name,
            persist_directory=str(self.persist_dir),
            embedding_function=self._embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_summary(self, *, video_id: str, summary: str) -> bool:
        """
        要約テキストを video_id と紐付けてChromaへ登録する。
        """
        normalized_summary = summary.strip()
        if not normalized_summary:
            raise ValueError("summary must not be empty.")
        if not video_id:
            raise ValueError("video_id must not be empty.")

        doc_id = f"{video_id}-{uuid.uuid4().hex}"
        metadata = {"video_id": video_id}

        self._vector_store.add_texts(
            texts=[normalized_summary],
            metadatas=[metadata],
            ids=[doc_id],
        )
        return True

    def _cosine01(self, q: np.ndarray, d: np.ndarray) -> float:
        # q,d は normalize_embeddings=True なら既に単位ベクトル
        # 念のため数値安定化
        denom = np.linalg.norm(q) * np.linalg.norm(d)
        if denom == 0 or not math.isfinite(denom):
            return 0.0
        cos = float(np.dot(q, d) / denom)
        # 範囲を変更　[-1,1] -> [0,1]
        return max(0.0, min(1.0, (cos + 1.0) / 2.0))

    def search(
        self,
        *,
        query: str,
        threshold: float = 0.8,
        max_gets: int = 3,
        fetch_k: int | None = None,  # 内部で多めに拾ってから閾値で絞る
    ) -> List[Dict[str, Any]]:
        """
        類似度が threshold 以上のドキュメントを最大 max_gets 件返す。
        返す score は必ず [0,1]。
        """
        if not query or max_gets <= 0:
            return []

        # 入力バリデーション
        threshold = max(0.0, min(1.0, float(threshold)))

        # クエリエンベディング
        q_vec = np.array(self._embeddings.embed_query(query), dtype=np.float32)

        # まず文書候補を広めに拾う（既定は 5x）
        if fetch_k is None:
            fetch_k = max_gets * 5

        try:
            # スコアは使わず、順序だけ利用（内部は cosine）
            docs = self._vector_store.similarity_search(query, k=fetch_k)
        except ValueError:
            # 空DBのときなど
            return []

        # 候補に対して明示的に類似度を計算し 0–1 に正規化してフィルタ
        doc_texts = [d.page_content for d in docs]
        if not doc_texts:
            return []

        doc_vecs = self._embeddings.embed_documents(doc_texts)  # 少数件なので再計算でOK
        scored: list[tuple[float, Any]] = []
        for d, d_vec in zip(docs, doc_vecs):
            rel = self._cosine01(q_vec, np.array(d_vec, dtype=np.float32))
            if rel >= threshold:
                scored.append((rel, d))

        # 類似度降順で上位 max_gets 件
        scored.sort(key=lambda t: t[0], reverse=True)
        out: List[Dict[str, Any]] = []
        for rel, d in scored[:max_gets]:
            out.append(
                {
                    "video_id": d.metadata.get("video_id"),
                    "content": d.page_content,
                    "score": rel,  # 常に 0–1
                }
            )
        return out
