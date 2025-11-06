# from __future__ import annotations

# from pathlib import Path
# from typing import List, Optional, Tuple

# import numpy as np

# from back.app.resources.template_retriever import TemplateEntry, TemplateRetriever


# class SearchExistingCodeService:
#     """
#     既存コードの検索と追加を担当するサービス。

#     主な機能
#     --------
#     - add(contents, code): 既存コードリストへ登録し、埋め込みも更新
#     - search(contents, thres, max_get): 類似コードを閾値付きで取得
#     """

#     DEFAULT_ID_PREFIX = "code"

#     def __init__(
#         self,
#         resource_dir: Optional[Path] = None,
#     ) -> None:
#         """
#         resourcesディレクトリとTemplateRetrieverインスタンスの初期化

#         Parameters
#         ----------
#         resource_dir:
#             カスタムリソースディレクトリを使用したい場合に指定する。
#         retriever:
#             外部で共有済みの TemplateRetriever インスタンス。
#         """
#         base_dir = Path(__file__).resolve().parent.parent
#         default_resource_dir = base_dir / "resources" / "templates"
#         self.resource_dir = resource_dir or default_resource_dir

#         self.retriever = TemplateRetriever(self.resource_dir)

#     def add(self, contents: str, code: str) -> TemplateEntry:
#         """
#         テンプレートを永続化し、埋め込みとリソースを更新する。

#         Parameters
#         ----------
#         contents:
#             テンプレートの説明文・テーマ。
#         code:
#             Manim スクリプト本体。
#         template_id:
#             任意のIDを指定したい場合に使用する。未指定なら自動採番。

#         Returns
#         -------
#         TemplateEntry
#             登録されたテンプレート情報。

#         persist=Trueとすると、ファイルの更新を行う。Falseにするとメモリ上のみの追加となる。
#         """
#         new_id = self.retriever.allocate_template_id(prefix=self.DEFAULT_ID_PREFIX)

#         entry = TemplateEntry(
#             template_id=new_id,
#             theme=contents,
#             code=code,
#         )

#         embedding = self.retriever.encode(entry.theme)
#         self.retriever.append_entry(entry, embedding, persist=True)

#         return entry

#     def search(
#         self,
#         contents: str,
#         thres: float = 0.8,
#         max_get: int = 3,
#     ) -> List[Tuple[str, float]]:
#         """
#         コサイン類似度が閾値以上のテンプレートを最大 `max_get` 件返す。

#         Parameters
#         ----------
#         contents:
#             検索に使用する説明文。
#         thres:
#             類似度の下限値。満たさない場合は除外する。
#         max_get:
#             取得上限件数。

#         Returns
#         -------
#         List[Tuple[str, float]]
#             (テンプレートの説明, 類似度スコア) のタプルリスト。
#         """
#         # 例外処理：テンプレートが存在しない場合
#         if not self.retriever.templates or self.retriever.embeddings.size == 0:
#             return []

#         query = self.retriever.encode(contents)
#         norm = np.linalg.norm(query)
#         if norm == 0:
#             return []
#         query = query / norm

#         top_hits = self.retriever.topk(query, k=max_get)

#         results: List[Tuple[str, float]] = []
#         for idx, score in top_hits:
#             if score < thres:
#                 continue
#             entry = self.retriever.templates[idx]
#             results.append((entry.theme, score))
#         return results

#     def delete_latest(self) -> TemplateEntry:
#         """
#         最も新しく追加されたテンプレートを削除し、リソースを更新する。

#         Returns
#         -------
#         TemplateEntry
#             削除されたテンプレートの情報。

#         presist=Trueとすると、ファイルの更新を行う。Falseにするとメモリ上のみの削除となる。
#         """
#         return self.retriever.remove_latest(persist=True)
