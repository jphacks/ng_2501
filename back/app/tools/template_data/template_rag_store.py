from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class TemplateRAGStore:
    """
    Chroma ベクトルストアを介してテンプレート要約を永続化・検索するヘルパー。
    """

    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent  # back/app/tools
        self.persist_dir = Path(base_dir / "embeding_data" / "template_chroma_db")
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.collection_name = "template_summaries"
        self.embedding_model = "cl-nagoya/ruri-v3-30m"

        self._embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self._vector_store = Chroma(
            collection_name=self.collection_name,
            persist_directory=str(self.persist_dir),
            embedding_function=self._embeddings,
        )

    def add_summary(self, *, video_id: str, summary: str) -> Dict[str, Any]:
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
        self._vector_store.persist()

        return True

    def search(
        self,
        *,
        query: str,
        threshold: float = 0.8,
        max_gets: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        類似度が threshold 以上のドキュメントを最大 max_gets 件取得する。
        """
        if max_gets <= 0:
            return []

        try:
            results = self._vector_store.similarity_search_with_relevance_scores(
                query,
                k=max_gets,
            )
        except ValueError:
            # ベクトルストアが空の場合は ValueError が発生する
            return []

        matches: List[Dict[str, Any]] = []
        for document, score in results:
            if score is None or score < threshold:
                continue
            matches.append(
                {
                    "video_id": document.metadata.get("video_id"),
                    "content": document.page_content,
                }
            )
        return matches
