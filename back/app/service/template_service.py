from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from back.app.tools.template_data.template_rag_store import TemplateRAGStore


load_dotenv()


class TemplateService:
    """
    Manimコードの要約生成と、RAGベクトルストアへの登録/検索を束ねるサービス。
    """

    def __init__(self) -> None:
        self.summary_model = "gemini-2.5-flash-lite"
        self.google_api_key = os.getenv("GEMINI_API_KEY")

        self._rag_store = TemplateRAGStore()
        self._summary_llm: Optional[ChatGoogleGenerativeAI] = None

    def _ensure_summary_llm(self) -> ChatGoogleGenerativeAI:
        if not self.google_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        if self._summary_llm is None:
            self._summary_llm = ChatGoogleGenerativeAI(
                model=self.summary_model,
                google_api_key=self.google_api_key,
                temperature=0.2,
                max_output_tokens=180,
            )
        return self._summary_llm

    @staticmethod
    def _extract_llm_text(message) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
            return "\n".join(parts).strip()
        return str(content).strip()

    def _summarize_manim_code(self, manim_code: str) -> str:
        llm = self._ensure_summary_llm()
        messages = [
            SystemMessage(
                content=(
                    "あなたは数学教育向けManimコードの要約アシスタントです。"
                    "コードが何を説明しているかを日本語で150文字程度にまとめてください。"
                    "後から類似検索しやすいように数学用語を含めてください。"
                )
            ),
            HumanMessage(
                content=(
                    "次のManimコードを要約してください。\n"
                    "```python\n"
                    f"{manim_code}\n"
                    "```\n"
                )
            ),
        ]
        response = llm.invoke(messages)
        summary = self._extract_llm_text(response)
        return summary

    def add(
        self,
        *,
        video_id: str,
        manim_code: str,
    ) -> bool:
        """
        Manimコードを要約し、RAGストアに登録する。
        """
        if not video_id:
            raise ValueError("video_id must not be empty.")
        if not manim_code:
            raise ValueError("manim_code must not be empty.")

        try:
            summary_text = self._summarize_manim_code(manim_code)
            normalized_summary = summary_text.strip()
            if not normalized_summary:
                raise ValueError("summary must not be empty.")
            is_success = self._rag_store.add_summary(
                video_id=video_id, summary=normalized_summary
            )
            return is_success
        except Exception as e:
            raise ValueError(f"Failed to add summary to RAG store: {e}")

    def search(
        self,
        *,
        query: str,
        max_gets: int = 12,
    ) -> List[Dict[str, Any]]:
        """RAGストアから類似テンプレートを検索する。"""
        if not query:
            return []
        return self._rag_store.search(query=query, max_gets=max_gets)
