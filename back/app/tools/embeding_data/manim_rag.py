import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

MANIM_REF_PATTERN = re.compile(r"manim[\.\w]+")
ERROR_PHRASE_PATTERN = re.compile(
    r"(?:AttributeError|TypeError|ValueError|LaTeX|ImportError|SyntaxError|NameError).*"
)

DEFAULT_COLLECTION_NAME = "manim_docs"
DEFAULT_EMBED_MODEL = "jinaai/jina-code-embeddings-1.5b"
DEFAULT_MAX_DOC_PREVIEW = 400


@lru_cache(maxsize=None)
def _load_chroma(
    persist_directory: str,
    collection_name: str,
    embedding_model: str,
) -> Chroma:
    embedding_function = HuggingFaceEmbeddings(model_name=embedding_model)
    return Chroma(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_function=embedding_function,
    )


def _format_doc_page(result) -> str:
    url = result.metadata.get("source_url", "") if result.metadata else ""
    full_name = result.metadata.get("full_name", "") if result.metadata else ""
    snippet = (result.page_content or "")[:DEFAULT_MAX_DOC_PREVIEW]
    suffix = "..." if len(result.page_content or "") > DEFAULT_MAX_DOC_PREVIEW else ""
    lines = [
        f"- {full_name}".rstrip(),
        f"{snippet}{suffix}",
    ]
    if url:
        lines.append(f"URL: {url}")
    return "\n".join(lines) + "\n"


class ManimDocsRAG:
    """Utility wrapper around the persisted Manim documentation ChromaDB."""

    def __init__(
        self,
        *,
        persist_subdir: Optional[Path] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBED_MODEL,
        logger: Optional[logging.Logger] = None,
    ):
        base_dir = Path(__file__).resolve().parent
        self.persist_directory = Path(persist_subdir or base_dir / "manim_chroma_db")
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.logger = logger or logging.getLogger(__name__)

    def _ctx(self, message: str, log_context: Optional[str]) -> str:
        return f"[{log_context}] {message}" if log_context else message

    def _db(self) -> Chroma:
        if not self.persist_directory.exists():
            raise FileNotFoundError(
                f"Chroma persist directory not found: {self.persist_directory}"
            )
        return _load_chroma(
            str(self.persist_directory),
            self.collection_name,
            self.embedding_model,
        )

    def similarity_search(
        self,
        query: str,
        *,
        k: int = 3,
        log_context: Optional[str] = None,
    ):
        self.logger.debug(
            self._ctx(
                f"RAG similarity_search query={query!r} k={k}",
                log_context,
            )
        )
        db = self._db()
        return db.similarity_search(query, k=k)

    def diagnostics_report(
        self,
        diagnostics: Iterable[dict],
        *,
        k: int = 2,
        max_sections: int = 5,
        log_context: Optional[str] = None,
    ) -> str:
        diagnostics = list(diagnostics or [])
        self.logger.debug(
            self._ctx(
                f"RAG diagnostics_report count={len(diagnostics)} k={k}",
                log_context,
            )
        )
        if not diagnostics:
            return "No related documentation found."

        db = self._db()
        seen_urls: set[str] = set()
        rule_to_docs: dict[str, list[str]] = {}

        for idx, diag in enumerate(diagnostics, start=1):
            message = diag.get("message", "")
            rule = diag.get("rule", "unknown")
            manim_refs = MANIM_REF_PATTERN.findall(message)
            query = " ".join(manim_refs) if manim_refs else message[:160]

            self.logger.debug(
                self._ctx(
                    f"RAG diagnostics[{idx}] rule={rule} query={query!r}",
                    log_context,
                )
            )

            results = db.similarity_search(query, k=k)
            docs = []
            for result in results:
                url = result.metadata.get("source_url", "") if result.metadata else ""
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                docs.append(_format_doc_page(result))

            if docs:
                rule_to_docs.setdefault(rule, []).extend(docs)
                self.logger.debug(
                    self._ctx(
                        f"RAG diagnostics[{idx}] hits={len(docs)}",
                        log_context,
                    )
                )

        if not rule_to_docs:
            self.logger.info(self._ctx("RAG diagnostics no related docs", log_context))
            return "No related documentation found."

        sections = []
        for rule, docs in rule_to_docs.items():
            section = f"### Rule: {rule}\n" + "\n".join(docs[:2])
            sections.append(section)
            if len(sections) >= max_sections:
                break

        combined = "\n\n".join(sections)
        self.logger.debug(
            self._ctx(
                f"RAG diagnostics aggregated_len={len(combined)}",
                log_context,
            )
        )
        return combined

    def runtime_error_report(
        self,
        inner_error: str,
        *,
        k: int = 3,
        max_results: int = 6,
        log_context: Optional[str] = None,
    ) -> str:
        text = inner_error or ""
        self.logger.debug(
            self._ctx(
                f"RAG runtime_error_report len={len(text)} k={k}",
                log_context,
            )
        )
        if not text.strip():
            return "No related documentation found."

        db = self._db()
        seen_urls: set[str] = set()

        base_queries = MANIM_REF_PATTERN.findall(text)
        error_phrases = ERROR_PHRASE_PATTERN.findall(text)
        if error_phrases:
            base_queries.extend(error_phrases)

        if not base_queries:
            base_queries.append(text[:200])

        aggregated: list[str] = []
        for idx, query in enumerate(base_queries[:4], start=1):
            self.logger.debug(
                self._ctx(
                    f"RAG runtime[{idx}] query={query!r}",
                    log_context,
                )
            )
            results = db.similarity_search(query, k=k)
            for result in results:
                url = result.metadata.get("source_url", "") if result.metadata else ""
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                aggregated.append(_format_doc_page(result))
                if len(aggregated) >= max_results:
                    break
            if len(aggregated) >= max_results:
                break

        if not aggregated:
            self.logger.info(self._ctx("RAG runtime no related docs", log_context))
            return "No related documentation found."

        combined = "\n\n".join(aggregated)
        self.logger.debug(
            self._ctx(
                f"RAG runtime aggregated_len={len(combined)}",
                log_context,
            )
        )
        return combined
