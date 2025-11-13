from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from back.app.model.model import VideoDatabase


class TemplateRAGStore:
    """
    Chroma ベクトルストアを介してテンプレート要約を永続化・検索するヘルパー。
    """

    def __init__(self) -> None:
        load_dotenv()

        base_dir = Path(__file__).resolve().parent  # back/app/tools/template_data
        self.persist_dir = base_dir / "template_chroma_db"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.template_dir = base_dir / "template_code_with_video"
        self.seed_marker = self.persist_dir / ".templates_seeded"

        workspace_root = Path(
            os.getenv("WORKSPACE_PATH", str(base_dir.parent.parent.parent))
        )
        self.scripts_dir = Path(
            os.getenv("MANIM_SCRIPTS_PATH", str(workspace_root / "tmp"))
        )
        self.videos_dir = Path(
            os.getenv("VIDEO_OUTPUT_PATH", str(workspace_root / "media" / "videos"))
        )
        self.prompts_dir = Path(
            os.getenv("USER_INSTRUCTION_PATH", str(workspace_root / "prompts"))
        )

        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.summary_cache_path = self.template_dir / "template_summary_cache.json"
        self._summary_cache = self._load_summary_cache()

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

        self._maybe_seed_templates()

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
        max_gets: int = 12,
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

    # --- 初期テンプレート投入処理 ---

    def _maybe_seed_templates(self) -> None:
        """
        template_code_with_video 内にあるテンプレートを
        初回のみ VideoDatabase とベクトルDBへ投入する。
        """
        if self.seed_marker.exists():
            return
        if not self.template_dir.exists():
            return

        templates = self._collect_template_pairs()
        if not templates:
            return

        video_db = VideoDatabase()
        seeded = False

        for template in templates:
            try:
                script_text = template["script_path"].read_text(encoding="utf-8")
            except FileNotFoundError:
                continue

            video_id = template["video_id"]

            # 常に最新のテンプレート資産を配置
            self._copy_script_asset(video_id, script_text)
            self._copy_video_asset(video_id, template["video_path"])
            prompt_path = self._ensure_prompt_file(video_id, template["name"])

            if video_db.get_video(video_id) is None:
                generate_id = video_db.generate_prompt()
                video_db.generate_video(
                    generate_id=generate_id,
                    video_id=video_id,
                    video_path=str(Path(video_id) / "480p15" / "GeneratedScene.mp4"),
                    prompt_path=prompt_path,
                    manim_code_path=f"{video_id}.py",
                )

            summary_text = self._build_summary_from_script(
                video_id=video_id,
                template_name=template["name"],
                script_text=script_text,
            )
            try:
                self._vector_store.delete(ids=[video_id])
            except ValueError:
                pass
            self._vector_store.add_texts(
                texts=[summary_text],
                metadatas=[{"video_id": video_id}],
                ids=[video_id],
            )
            seeded = True

        if seeded:
            self.seed_marker.write_text(datetime.utcnow().isoformat())
    def _collect_template_pairs(self) -> List[Dict[str, Any]]:
        """
        template_code_with_video ディレクトリから (.py, .mp4) のペアを抽出する。
        """
        pairs: List[Dict[str, Any]] = []
        for script_path in sorted(self.template_dir.glob("*.py")):
            name = script_path.stem
            video_path = self.template_dir / f"{name}.mp4"
            if not video_path.exists():
                continue
            video_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"template::{name}"))
            pairs.append(
                {
                    "name": name,
                    "video_id": video_id,
                    "script_path": script_path,
                    "video_path": video_path,
                }
            )
        return pairs

    def _copy_script_asset(self, video_id: str, script_text: str) -> None:
        """
        テンプレートのmanimコードを MANIM_SCRIPTS_PATH 配下へ配置する。
        """
        dest = self.scripts_dir / f"{video_id}.py"
        dest.write_text(script_text, encoding="utf-8")

    def _copy_video_asset(self, video_id: str, src_video: Path) -> None:
        """
        テンプレートのmp4を VIDEO_OUTPUT_PATH 配下へ配置する。
        """
        target_dir = self.videos_dir / video_id / "480p15"
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_video, target_dir / "GeneratedScene.mp4")

    def _ensure_prompt_file(self, video_id: str, template_name: str) -> str:
        """
        VideoDatabase登録用のダミープロンプトを1つ生成する。
        """
        prompt_file = self.prompts_dir / f"{video_id}.json"
        if not prompt_file.exists():
            prompt_payload = {
                "prompt": [
                    {
                        "trial": 1,
                        "content": (
                            f"テンプレート {template_name} の初期スクリプト。"
                            "template_code_with_video から移行されました。"
                        ),
                        "enhance_prompt": "",
                    }
                ]
            }
            prompt_file.write_text(
                json.dumps(prompt_payload, ensure_ascii=False, indent=4),
                encoding="utf-8",
            )
        return prompt_file.name

    def _load_summary_cache(self) -> Dict[str, Any]:
        if self.summary_cache_path.exists():
            try:
                data = json.loads(self.summary_cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                return {}
        return {}
    def _build_summary_from_script(
        self, *, video_id: str, template_name: str, script_text: str
    ) -> str:
        """
        template_summary_cache.json にある要約をそのまま返す。
        """
        cache_entry = self._summary_cache.get(template_name)
        if cache_entry:
            summary = cache_entry.get("summary", "").strip()
            if summary:
                return summary
        raise KeyError(
            f"Summary for template {template_name} is missing. "
            "Please ensure template_summary_cache.json is up to date."
        )
