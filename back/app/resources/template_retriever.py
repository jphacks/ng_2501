from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

import numpy as np

from back.app.resources.template_encoder import TemplateEncoder


@dataclass(frozen=True)
class TemplateEntry:
    """
    テンプレートリソースに保存される1件分のエントリ。
    """

    template_id: str
    theme: str
    code: str


class TemplateRetriever:
    """
    テンプレート情報の読み込みと埋め込み検索を担当するクラス。
    """

    MODEL_NAME = "cl-nagoya/ruri-v3-30m"

    def __init__(self, resource_dir: Path) -> None:
        """
        テンプレート情報と埋め込みを読み込み、埋め込みモデルを初期化する。
        """
        self.resource_dir = resource_dir
        self.resource_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_path = self.resource_dir / "theme_embeddings.npy"
        self.templates_path = self.resource_dir / "manim_template.jsonl"

        self.templates: List[TemplateEntry] = self._load_templates()
        self.embeddings: np.ndarray = self._load_embeddings()
        if self.embeddings.shape[0] != len(self.templates):
            raise ValueError("Template count and embedding rows mismatch.")

        self._template_by_id: Dict[str, TemplateEntry] = {
            entry.template_id: entry for entry in self.templates
        }
        self._sequence_pattern_cache: Dict[str, Pattern[str]] = {}

        self.encoder = TemplateEncoder(self.MODEL_NAME)

    def _load_templates(self) -> List[TemplateEntry]:
        """
        JSONL からテンプレート情報を読み込む。ファイルが無ければ空リストを返す。
        """
        entries: List[TemplateEntry] = []
        if not self.templates_path.exists():
            return entries
        with self.templates_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                payload = line.strip()
                if not payload:
                    continue
                record = json.loads(payload)
                entries.append(
                    TemplateEntry(
                        template_id=record["id"],
                        theme=record["theme"],
                        code=record.get("code", ""),
                    )
                )
        return entries

    def _load_embeddings(self) -> np.ndarray:
        """
        埋め込み行列を取得し、各行が単位ベクトルになるよう正規化する。
        """
        if not self.embeddings_path.exists():
            return np.empty((0, 0), dtype=np.float32)
        matrix = np.load(self.embeddings_path)
        if matrix.size == 0:
            return matrix
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        return matrix / norms

    def encode(self, text: str, *, max_length: int = 256) -> np.ndarray:
        """
        テキストをエンコードし、正規化済みの文ベクトルを返す。
        """
        return self.encoder.encode(text, max_length=max_length)

    def allocate_template_id(
        self, template_id: Optional[str] = None, *, prefix: str = "code"
    ) -> str:
        """
        新しいテンプレートIDを取得する。テンプレートID指定時は重複チェックのみ行う。
        """
        if template_id:
            if template_id in self._template_by_id:
                raise ValueError("指定された template_id は既に存在します。")
            return template_id
        next_seq = self._compute_next_sequence(prefix)
        return f"{prefix}{next_seq}"

    def append_entry(
        self, entry: TemplateEntry, embedding: np.ndarray, *, persist: bool = False
    ) -> None:
        """
        新しいテンプレートと埋め込みを登録し、必要に応じて永続化する。
        """
        if embedding.ndim != 1:
            raise ValueError("Embedding must be a 1-D vector.")
        norm = np.linalg.norm(embedding)
        if norm == 0:
            raise ValueError("Embedding norm is zero.")
        normalized = (embedding / norm).astype(np.float32)

        if entry.template_id in self._template_by_id:
            raise ValueError(
                f"template_id '{entry.template_id}' is already registered."
            )

        if self.embeddings.size == 0:
            self.embeddings = normalized[None, :]
        else:
            self.embeddings = np.vstack([self.embeddings, normalized])

        self.templates.append(entry)
        self._template_by_id[entry.template_id] = entry

        if persist:
            self._append_template_to_disk(entry)
            self._save_embeddings()

    def get_by_id(self, template_id: str) -> Optional[TemplateEntry]:
        return self._template_by_id.get(template_id)

    def topk(self, query: np.ndarray, *, k: int = 3) -> List[Tuple[int, float]]:
        """
        類似度の高い順に上位 k 件の (インデックス, スコア) を返す。
        """
        if self.embeddings.size == 0:
            return []
        scores = self.embeddings @ query
        ranked = np.argsort(scores)[::-1]
        return [(int(idx), float(scores[idx])) for idx in ranked[:k]]

    def remove_latest(self, *, persist: bool = False) -> TemplateEntry:
        """
        最後に追加されたテンプレートを削除し、必要に応じて永続化する。
        """
        if not self.templates:
            raise ValueError("テンプレートが登録されていません。")

        removed_entry = self.templates.pop()
        self._template_by_id.pop(removed_entry.template_id, None)

        if self.embeddings.size == 0 or self.embeddings.shape[0] <= 1:
            self.embeddings = np.empty((0, 0), dtype=np.float32)
        else:
            self.embeddings = self.embeddings[:-1, :]

        if persist:
            self._write_templates_file()
            self._save_embeddings()

        return removed_entry

    def _compute_next_sequence(self, prefix: str) -> int:
        pattern = self._get_id_pattern(prefix)
        max_seq = 0
        for entry in self.templates:
            match = pattern.match(entry.template_id)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return max_seq + 1

    def _append_template_to_disk(self, entry: TemplateEntry) -> None:
        payload = {
            "id": entry.template_id,
            "theme": entry.theme,
            "code": entry.code,
        }
        with self.templates_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False))
            fh.write("\n")

    def _write_templates_file(self) -> None:
        if not self.templates:
            self.templates_path.write_text("", encoding="utf-8")
            return

        lines = []
        for entry in self.templates:
            payload = {
                "id": entry.template_id,
                "theme": entry.theme,
                "code": entry.code,
            }
            lines.append(json.dumps(payload, ensure_ascii=False))
        self.templates_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _save_embeddings(self) -> None:
        np.save(self.embeddings_path, self.embeddings)

    def _get_id_pattern(self, prefix: str) -> Pattern[str]:
        pattern = self._sequence_pattern_cache.get(prefix)
        if pattern is None:
            pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
            self._sequence_pattern_cache[prefix] = pattern
        return pattern
