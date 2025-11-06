"""
manim 0.19.0 専用の linter（色は直接名のみチェック + 属性呼び出し検出）

検出内容（= 実行時エラーになりやすいもの中心）:
- 使用できないクラス / 関数 / 定数（manim に存在しない裸名呼び出し）…… MANIM001
- 使用できないメソッド / 関数呼び出し（非 callable を呼び出し）…… MANIM020
- 存在しないキーワード引数（__init__ / 関数に **kwargs が無い場合のみ）…… MANIM030
- サブクラスの __init__ が super().__init__(kw=...) に明示指定する
  「予約キーワード」と多重指定の衝突（multiple values）…… MANIM031
- 色の直接名が未定義 / 非 Color …… MANIM041 / MANIM040
- manim シンボルの「属性呼び出し」で、属性が存在しない / 非 callable …… MANIM010 / MANIM020
- 属性呼び出しのレシーバ自体が manim に存在しない …… MANIM001
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import builtins as py_builtins
import manim


# ============================================================
# manim API 情報
# ============================================================

class ManimAPIDatabase:
    """manim 0.19.0 の API 情報を introspection で集める"""

    def __init__(self) -> None:
        self.globals: Dict[str, Any] = dict(vars(manim))

        # Color 判定: to_hex / to_rgb / to_rgba を持つオブジェクトを Color とみなす
        self.colors: Set[str] = set()
        for name, obj in self.globals.items():
            if callable(obj):
                continue
            if hasattr(obj, "to_hex") or hasattr(obj, "to_rgb") or hasattr(obj, "to_rgba"):
                self.colors.add(name)

    def has_symbol(self, name: str) -> bool:
        return name in self.globals

    def get_symbol(self, name: str) -> Any:
        return self.globals.get(name, None)

    def is_color_symbol(self, name: str) -> bool:
        return name in self.colors


# ============================================================
# Lint メッセージ
# ============================================================

@dataclass
class LintMessage:
    filename: str
    lineno: int
    col_offset: int
    level: str  # "WARNING" / "ERROR"
    code: str   # 例: "MANIM001"
    message: str

    def format(self) -> str:
        return f"{self.filename}:{self.lineno}:{self.col_offset}: {self.level} {self.code} {self.message}"


# ============================================================
# Linter 本体
# ============================================================

class Manim019Linter(ast.NodeVisitor):
    """
    実行時エラーになりやすい箇所のみを静的検出。
    色は「直接名」のみチェック。変数は辿らない。
    属性呼び出し（Axes.s(...), Line.foo(...)) も検出。
    """

    COLOR_KWARGS = {"color", "stroke_color", "fill_color", "background_color"}

    # フォールバック: 既知の予約キーワード衝突（ソース解析できなかった場合）
    _CONFLICTING_KW_FALLBACK: Dict[str, Set[str]] = {
        # Sector(radius=...) が super で outer_radius/inner_radius を渡すため衝突
        "Sector": {"outer_radius", "inner_radius"},
    }

    def __init__(self, filename: str, api_db: ManimAPIDatabase) -> None:
        self.filename = filename
        self.api_db = api_db
        self.messages: List[LintMessage] = []

        self.star_import: bool = False  # `from manim import *` があるか
        self.scope_stack: List[Set[str]] = [set()]  # 定義名トラッキング

        # 安定した builtins 判定
        self.python_builtins: Set[str] = {
            name for name in dir(py_builtins) if not name.startswith("_")
        }

        # super().__init__ に明示で渡される予約キーワードのキャッシュ
        self._reserved_kw_cache: Dict[str, Set[str]] = {}
        # 解析中クラスの基底名セット（Scene系の検出用）
        self.class_bases_stack: List[Set[str]] = []

    # ---------- スコープ管理 ----------
    def push_scope(self) -> None:
        self.scope_stack.append(set())

    def pop_scope(self) -> None:
        self.scope_stack.pop()

    def define_name(self, name: str) -> None:
        self.scope_stack[-1].add(name)

    def is_defined(self, name: str) -> bool:
        return any(name in s for s in reversed(self.scope_stack))

    # ---------- メッセージ ----------
    def add_message(self, node: ast.AST, code: str, message: str, level: str = "WARNING") -> None:
        self.messages.append(
            LintMessage(
                filename=self.filename,
                lineno=getattr(node, "lineno", 0),
                col_offset=getattr(node, "col_offset", 0),
                level=level,
                code=code,
                message=message,
            )
        )

    # ========================================================
    # import 文
    # ========================================================

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # from manim import * 検出 + 個別 import 名は定義扱い
        if node.module == "manim":
            for alias in node.names:
                if alias.name == "*":
                    self.star_import = True
                else:
                    self.define_name(alias.asname or alias.name)
        else:
            for alias in node.names:
                if alias.name != "*":
                    self.define_name(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        # import numpy as np -> "np" を定義扱い
        for alias in node.names:
            top = (alias.asname or alias.name).split(".")[0]
            self.define_name(top)
        self.generic_visit(node)

    # ========================================================
    # 変数定義 / スコープ（関数・クラス・代入・例外・ラムダ・内包表記）
    # ========================================================

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.define_name(node.name)
        self.push_scope()
        for arg in node.args.args:
            self.define_name(arg.arg)
        # *args / **kwargs
        if node.args.vararg:
            self.define_name(node.args.vararg.arg)
        if node.args.kwarg:
            self.define_name(node.args.kwarg.arg)
        self.generic_visit(node)
        self.pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.define_name(node.name)
        self.push_scope()
        for arg in node.args.args:
            self.define_name(arg.arg)
        if node.args.vararg:
            self.define_name(node.args.vararg.arg)
        if node.args.kwarg:
            self.define_name(node.args.kwarg.arg)
        self.generic_visit(node)
        self.pop_scope()

    def _base_name_of(self, node: ast.expr) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.define_name(node.name)
        base_names = {bn for base in node.bases if (bn := self._base_name_of(base))}
        self.class_bases_stack.append(base_names)
        self.push_scope()
        try:
            self.generic_visit(node)
        finally:
            self.pop_scope()
            self.class_bases_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            # 左辺に現れる Name は visit_Name(Store) でも拾うが、
            # タプル/リストのネストなどで取りこぼさないため一応辿っておく
            self._define_targets(t)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._define_targets(node.target)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # 追加: Store 文脈は「定義」とみなす（for/with/:= 内包表記含む）
        if isinstance(node.ctx, ast.Store):
            self.define_name(node.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # except Exception as e: の e を定義
        if node.name and isinstance(node.name, str):
            self.define_name(node.name)
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # ラムダの仮引数スコープ
        self.push_scope()
        for arg in node.args.args:
            self.define_name(arg.arg)
        if node.args.vararg:
            self.define_name(node.args.vararg.arg)
        if node.args.kwarg:
            self.define_name(node.args.kwarg.arg)
        # 本体を訪問
        self.generic_visit(node)
        self.pop_scope()

    # ---- 内包表記は独立スコープとして扱う（ターゲット変数が外側に漏れない） ----

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension_like(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension_like(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension_like(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension_like(node)

    def _visit_comprehension_like(self, node: ast.AST) -> None:
        # 新スコープでターゲット変数を定義（外側に出さない）
        self.push_scope()
        if isinstance(node, (ast.ListComp, ast.SetComp)):
            for gen in node.generators:
                self.visit(gen.target)  # Store -> visit_Name が define する
                self.visit(gen.iter)
                for iff in gen.ifs:
                    self.visit(iff)
            self.visit(node.elt)
        elif isinstance(node, ast.DictComp):
            for gen in node.generators:
                self.visit(gen.target)
                self.visit(gen.iter)
                for iff in gen.ifs:
                    self.visit(iff)
            self.visit(node.key)
            self.visit(node.value)
        elif isinstance(node, ast.GeneratorExp):
            for gen in node.generators:
                self.visit(gen.target)
                self.visit(gen.iter)
                for iff in gen.ifs:
                    self.visit(iff)
            self.visit(node.elt)
        self.pop_scope()

    def _define_targets(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.define_name(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._define_targets(elt)
        # 属性代入（obj.x = ...）や subscript（a[0] = ...）は「新規定義」ではないので無視

    # ========================================================
    # Call（関数/クラス呼び出し & 属性呼び出し）
    # ========================================================

    def _current_camera_symbol(self) -> str:
        if not self.class_bases_stack:
            return "Camera"
        bases = self.class_bases_stack[-1]
        if "MovingCameraScene" in bases:
            return "MovingCamera"
        if "ThreeDScene" in bases:
            return "ThreeDCamera"
        return "Camera"

    def _is_self_camera_attr(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and node.attr == "camera"
        )

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # 裸名呼び出し（Dot(...), Axes(...), Line(...), ...）
        if isinstance(func, ast.Name) and self.star_import:
            name = func.id
            if self.is_defined(name):
                pass  # ローカル定義（ユーザー関数/クラス/変数）
            elif name in self.python_builtins:
                pass  # 組み込み（range, abs, max, ...）
            elif self.api_db.has_symbol(name):
                self._check_manim_symbol_call(node, name, name)
            else:
                # from manim import * 前提で manim にない裸名の呼び出し → 実行時 NameError 相当
                self.add_message(
                    node,
                    code="MANIM001",
                    message=(
                        f"'{name}' は manim 0.19.0 のシンボルに存在しません。"
                    ),
                )

        # 属性呼び出し（Axes.s(...), Line.foo(...), Text.from_markup(...), etc.）
        elif isinstance(func, ast.Attribute):
            if self._is_self_camera_attr(func.value):
                cam_symbol = self._current_camera_symbol()
                if self.api_db.has_symbol(cam_symbol):
                    cam_obj = self.api_db.get_symbol(cam_symbol)
                    attr_name = func.attr
                    if not hasattr(cam_obj, attr_name):
                        self.add_message(
                            node,
                            code="MANIM010",
                            message=(
                                f"'self.camera'（{cam_symbol}）に属性 '{attr_name}' は存在しません。"
                            ),
                        )
                        self.generic_visit(node)
                        return
                    attr_obj = getattr(cam_obj, attr_name)
                    if not callable(attr_obj):
                        self.add_message(
                            node,
                            code="MANIM020",
                            message=(
                                f"'{cam_symbol}.{attr_name}' は関数/クラスではないため、呼び出せません。"
                            ),
                        )
                        self.generic_visit(node)
                        return
            if self.star_import:
                owner = func.value
                if isinstance(owner, ast.Name):
                    owner_name = owner.id
                    # ローカル定義や組み込みは対象外
                    if self.is_defined(owner_name) or owner_name in self.python_builtins:
                        pass
                    else:
                        # レシーバ（owner）が manim シンボルでない場合にも警告（未定義レシーバ）
                        if not self.api_db.has_symbol(owner_name):
                            # 例: Te.s(...) の Te が未定義（manim に存在しない）
                            self.add_message(
                                owner,
                                code="MANIM001",
                                message=(
                                    f"'{owner_name}' は manim 0.19.0 のシンボルに存在しません。"
                                ),
                            )
                            self.generic_visit(node)
                            return

                        # manim にある既知シンボル: 既存の属性チェックを実行
                        base_obj = self.api_db.get_symbol(owner_name)
                        attr_name = func.attr

                        if not hasattr(base_obj, attr_name):
                            self.add_message(
                                node,
                                code="MANIM010",
                                message=f"'{owner_name}' に属性 '{attr_name}' は存在しません。",
                            )
                        else:
                            attr_obj = getattr(base_obj, attr_name)
                            if not callable(attr_obj):
                                self.add_message(
                                    node,
                                    code="MANIM020",
                                    message=f"'{owner_name}.{attr_name}' は関数/クラスではないため、呼び出せません。",
                                )
                            else:
                                disp = f"{owner_name}.{attr_name}"
                                self._check_keyword_args(node, attr_obj, disp)
                                self._check_color_keywords_direct_only(node, disp)
                                self._check_reserved_keyword_conflicts(node, disp, attr_obj)

        self.generic_visit(node)

    def _check_manim_symbol_call(self, node: ast.Call, api_name: str, display_name: str) -> None:
        obj = self.api_db.get_symbol(api_name)

        # 非 callable 呼び出し → 実行時 TypeError 相当
        if not callable(obj):
            self.add_message(
                node,
                code="MANIM020",
                message=f"'{display_name}' は関数/クラスではないため、呼び出せません。",
            )
            return

        # 存在しないキーワード（**kwargs が無い場合のみ） → 実行時 TypeError 相当
        self._check_keyword_args(node, obj, display_name)

        # super().__init__ で既に指定される予約キーワードとの多重指定 → 実行時 multiple values
        self._check_reserved_keyword_conflicts(node, display_name, obj)

        # 色の直接名チェック（未定義/非 Color は実行時エラーになりやすい）
        self._check_color_keywords_direct_only(node, display_name)

    # ---------- キーワード引数存在チェック ----------
    def _check_keyword_args(self, node: ast.Call, obj: Any, display_name: str) -> None:
        try:
            sig = inspect.signature(obj)
        except (TypeError, ValueError):
            return
        params = sig.parameters
        param_names = {
            name
            for name, p in params.items()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        }
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

        for kw in node.keywords:
            if kw.arg is None:  # **kwargs
                continue
            if kw.arg not in param_names and not has_var_kw:
                self.add_message(
                    kw,
                    code="MANIM030",
                    message=(
                        f"'{display_name}' にキーワード引数 '{kw.arg}' は存在しません "
                        f"(manim 0.19.0 のシグネチャに含まれていません)。"
                    ),
                )

    # ---------- super().__init__ の予約キーワード衝突 ----------
    def _check_reserved_keyword_conflicts(self, node: ast.Call, display_name: str, obj: Any) -> None:
        reserved = self._reserved_keywords_for(display_name, obj)
        if not reserved:
            reserved = self._CONFLICTING_KW_FALLBACK.get(display_name, set())
        if not reserved:
            return
        for kw in node.keywords:
            if kw.arg in reserved:
                self.add_message(
                    kw,
                    code="MANIM031",
                    message=(
                        f"'{display_name}' にキーワード '{kw.arg}' を同時指定すると衝突が発生します。"
                        f" 内部実装で '{kw.arg}' がすでに指定されているため、多重指定になります。"
                        f" 予約キーワード: {', '.join(sorted(reserved))}"
                    ),
                )

    def _reserved_keywords_for(self, api_name: str, obj: Any) -> Set[str]:
        if api_name in self._reserved_kw_cache:
            return self._reserved_kw_cache[api_name]
        kws: Set[str] = set()
        try:
            target = getattr(obj, "__init__", obj)
            src = inspect.getsource(target)
            mod = ast.parse(src)

            class _SuperInitKWVisitor(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.found: Set[str] = set()
                def visit_Call(self, call: ast.Call) -> None:
                    if (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == "__init__"
                        and isinstance(call.func.value, ast.Call)
                        and isinstance(call.func.value.func, ast.Name)
                        and call.func.value.func.id == "super"
                    ):
                        for k in call.keywords:
                            if k.arg:
                                self.found.add(k.arg)
                    self.generic_visit(call)

            v = _SuperInitKWVisitor()
            v.visit(mod)
            kws = v.found
        except Exception:
            kws = set()
        self._reserved_kw_cache[api_name] = kws
        return kws

    # ---------- 色の直接名のみチェック ----------
    def _check_color_keywords_direct_only(self, node: ast.Call, display_name: str) -> None:
        """
        color, stroke_color, fill_color, background_color に対して、
        右辺が「裸の名前（Name）」で、かつローカル変数ではない場合のみチェック。
        - manim に存在しない → MANIM041（NameError 相当）
        - manim に存在するが Color ではない → MANIM040（型不整合で落ちやすい）
        """
        for kw in node.keywords:
            if kw.arg not in self.COLOR_KWARGS:
                continue
            v = kw.value
            if isinstance(v, ast.Name):
                name = v.id
                if self.is_defined(name):  # 変数は追跡しない
                    continue
                if self.api_db.has_symbol(name):
                    if not self.api_db.is_color_symbol(name):
                        self.add_message(
                            v,
                            code="MANIM040",
                            message=(
                                f"'{display_name}' の引数 '{kw.arg}' に指定された '{name}' は "
                                f"manim 0.19.0 の Color 定数ではありません。"
                            ),
                        )
                else:
                    self.add_message(
                        v,
                        code="MANIM041",
                        message=(
                            f"'{display_name}' の引数 '{kw.arg}' に指定された '{name}' は "
                            f"manim 0.19.0 のシンボルに存在しません。"
                        ),
                    )


# ============================================================
# ユーティリティ
# ============================================================

def classify_error_code(code: str) -> str:
    if code in ("MANIM040", "MANIM041"):
        return "ColorError"
    if code in ("MANIM030", "MANIM031"):
        return "ArgumentError"
    if code in ("MANIM001", "MANIM010", "MANIM011"):
        return "SymbolError"
    if code == "MANIM020":
        return "CallError"
    return "ManimLintWarning"


def lint_text_structured(
    text: str,
    filename: str = "<memory>",
    api_db: Optional[ManimAPIDatabase] = None,
) -> List[Dict[str, Any]]:
    """
    文字列ソースを直接 lint して構造化メッセージを返す。
    """
    if api_db is None:
        api_db = ManimAPIDatabase()

    try:
        tree = ast.parse(text, filename=filename)
    except SyntaxError as e:
        line_text = (e.text or "").rstrip("\n")
        lineno = e.lineno or 0
        col = (e.offset - 1) if e.offset and e.offset > 0 else 0
        return [
            {
                "filename": filename,
                "lineno": lineno,
                "col": col,
                "code_line": line_text,
                "pattern": "SyntaxError / SYNTAX",
                "message": e.msg,
                "code": "SYNTAX",
                "kind": "SyntaxError",
            }
        ]

    linter = Manim019Linter(filename, api_db)
    linter.visit(tree)
    lines = text.splitlines()

    results: List[Dict[str, Any]] = []
    for m in linter.messages:
        lineno = m.lineno
        line_text = lines[lineno - 1] if 1 <= lineno <= len(lines) else ""
        kind = classify_error_code(m.code)
        results.append(
            {
                "filename": m.filename,
                "lineno": lineno,
                "col": m.col_offset,
                "code_line": line_text,
                "pattern": f"{kind} / {m.code}",
                "message": m.message,
                "code": m.code,
                "kind": kind,
            }
        )
    return results


class ManimLinter:
    """
    BaseAgent などから呼び出しやすいラッパークラス。
    """

    def __init__(self, api_db: Optional[ManimAPIDatabase] = None) -> None:
        self.api_db = api_db or ManimAPIDatabase()

    def check_code(
        self, code: str, *, filename: str = "<generated>"
    ) -> Dict[str, Any]:
        issues = lint_text_structured(code, filename=filename, api_db=self.api_db)
        if not issues:
            return {
                "status": "pass",
                "issue_count": 0,
                "issues": [],
                "summary": "",
            }

        summary_lines: List[str] = []
        for item in issues:
            location = f"{item['filename']}:{item['lineno']}"
            detail = f"[{item['code']}] {item['message']}"
            line_preview = item["code_line"].strip()
            if line_preview:
                detail = f"{detail}\n    {line_preview}"
            summary_lines.append(f"- {location} {detail}")

        summary = "Manim linter warnings detected:\n" + "\n".join(summary_lines)
        return {
            "status": "fail",
            "issue_count": len(issues),
            "issues": issues,
            "summary": summary,
        }
