from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class TemplateRAGStore:
    """
    Chroma ベクトルストアを介してテンプレート要約を永続化・検索するヘルパー。
    """

    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parent  # back/app/tools/template_data
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

        doc_id = video_id  # video_id ごとに常に最新1件
        metadata = {"video_id": video_id}

        try:
            # 同一 video_id があれば先に削除して最新だけを保持
            self._vector_store.delete(where={"video_id": video_id})
        except ValueError:
            pass

        self._vector_store.add_texts(
            texts=[normalized_summary],
            metadatas=[metadata],
            ids=[doc_id],
        )
        return True

    def search(
        self,
        *,
        query: str,
        max_gets: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Chroma 既定の類似度で上位 max_gets 件の結果を返す。
        """
        if not query or max_gets <= 0:
            return []

        try:
            doc_scores = self._vector_store.similarity_search_with_relevance_scores(
                query, k=max_gets
            )
        except ValueError:
            # 空DBのときなど
            return []

        out: List[Dict[str, Any]] = []
        for doc, score in doc_scores:
            out.append(
                {
                    "video_id": doc.metadata.get("video_id"),
                    "content": doc.page_content,
                    "score": float(score), # scoreは[-1,1]の範囲のfloat
                }
            )
        return out
