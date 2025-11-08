"""
manim セキュリティチェック

- 目的:
  - Manim 実行用スクリプトから「描画以外の危険操作」を静的解析で検出・拒否（fail-closed：解析不能は NG）

- 方針（チェック内容）:
  - import 制限
    - 許可: `from manim import *` および `from manim import Scene, VGroup, ...`（相対 import は禁止）
    - 許可: `import numpy` / `import numpy as np`
    - 上記以外の import / from-import は NG
  - 参照解決
    - `np` → `numpy` のエイリアス解決、代入由来の関数参照（例: `f = np.save`）の FQN 解決
  - 危険ビルトインの呼び出し検出
    - `eval` / `exec` / `compile` / `__import__` / `getattr` / `globals` / `locals` / `vars` / `dir`
    - `getattr(x, "open"|"eval"|"exec"|...)` のような危険キー指定も検出
  - ファイル I/O の全面禁止
    - `open` / `io.open` / `Path.open` をモード不問で NG（読み取りも禁止）
    - `Path.read_text` / `Path.read_bytes` / `Path.write_text` / `Path.write_bytes` の呼び出しを検出して NG
  - NumPy のファイル I/O の禁止
    - `numpy.save/savez/savetxt/load/loadtxt/genfromtxt/fromfile/memmap` など
    - サブモジュール経由（例: `numpy.lib.format.open_memmap`）も検出
    - `ndarray.tofile` / `ndarray.dump` などのインスタンス I/O も NG
  - 外部コマンド実行の禁止
    - `subprocess.*` への到達を一律 NG（`shell` / `executable` 指定も悪性フラグ）
  - 反射・名前空間探索の抑止
    - `__builtins__` / `__globals__` / `__dict__` / `__mro__` / `__subclasses__` / `__getattribute__` などの危険ダンダー属性参照を検出
  - 関数取得経路の制限
    - 辞書/リスト/タプル等の Subscript 由来の関数呼び出し（例: `danger["f"](...)`）は一律 NG
    - さらに Subscript 由来でいったん変数へ束縛した別名（tainted alias）を介した呼び出しも NG
  - 構文エラー時の動作
    - `SyntaxError` 検出時は即 NG（fail-closed）
"""

import ast
from typing import List, Tuple, Optional, Dict, Set


# --- 完全修飾名で NG な関数/メソッド ---
BANNED_FQNS: Set[str] = {
    # メタ実行（builtins）
    "builtins.eval",
    "builtins.exec",
    "builtins.compile",
    "builtins.__import__",
    "importlib.import_module",
    "builtins.getattr",
    "builtins.globals",
    "builtins.locals",
    "builtins.vars",
    "builtins.dir",
    # 代表的 NumPy I/O（直接指定）
    "numpy.save",
    "numpy.savez",
    "numpy.savez_compressed",
    "numpy.savetxt",
    "numpy.load",
    "numpy.loadtxt",
    "numpy.genfromtxt",
    "numpy.memmap",
    "numpy.fromfile",
    "numpy.lib.format.open_memmap",
}

# NumPy の I/O サフィックス（サブモジュール経由でも封じる）
NUMPY_IO_SUFFIXES: Set[str] = {
    "save",
    "savez",
    "savez_compressed",
    "savetxt",
    "load",
    "loadtxt",
    "genfromtxt",
    "fromfile",
    "memmap",
    "open_memmap",
}

# 危険 prefix
BANNED_PREFIXES: Tuple[str, ...] = (
    "numpy.ctypeslib",  # 共有ライブラリ読込など
    "numpy.lib.format",  # open_memmap 等
    "subprocess",  # 外部コマンド全般
    "os",  # 念のため（import 自体が禁止だが FQN 観測でも弾く）
    "shutil",
)

PATH_WRITE_METHODS: Set[str] = {"write_text", "write_bytes"}
PATH_READ_METHODS: Set[str] = {"read_text", "read_bytes"}

# ndarray 由来のファイル/シリアライズ I/O（受け手に依らず属性名でブロック）
NDARRAY_IO_ATTRS: Set[str] = {"tofile", "dump"}

# --- 反射・辞書経由で危険になりやすいダンダー ---
SUSPICIOUS_DUNDERS: Set[str] = {
    "__builtins__",
    "__globals__",
    "__dict__",
    "__mro__",
    "__subclasses__",
    "__getattribute__",
}

# __builtins__ 等から取り出されたら NG なキー
DANGEROUS_BUILTIN_KEYS: Set[str] = {
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "getattr",
}

# subprocess で危険になり得る KW
SUBPROC_DANGEROUS_KW: Set[str] = {"shell", "executable"}


def _const_str(n: ast.AST) -> Optional[str]:
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None


class StrictGuard(ast.NodeVisitor):
    """
    - 許可 import（from manim import * / from manim import X... / import numpy[ as np]）のみ許可
    - numpy/np の解決 + 代入による関数参照の伝播を追跡
    - getattr/__import__/globals()/locals()/vars()/dir() を検出（FQN/エイリアス含む）
    - __builtins__/__globals__/__dict__ 経由の辞書アクセスを検出
    - subprocess.* を一律 NG（到達時は KW も検査）
    - Path I/O / ndarray I/O は**受け手に依らず**属性名で検出
    - 関数が Subscript 由来（辞書/リスト/タプル等から取得）なら一律 NG
      さらに Subscript 由来で名前に束縛された場合（tainted alias）からの呼び出しも NG
    """

    def __init__(self) -> None:
        self.findings: List[Tuple[int, str]] = []
        # as エイリアス（モジュール名解決: {"np": "numpy", "numpy": "numpy"}）
        self.module_alias: Dict[str, str] = {}
        # 代入された参照の簡易解決（f = np.save / y = numpy.lib.format）
        # 値は "numpy.save" や "numpy.lib.format" などの FQN
        self.name_bindings: Dict[str, str] = {}
        # Subscript 由来で束縛された「汚染済みの別名」
        self.tainted_from_subscript: Set[str] = set()

    # ---------- 許可 import 判定 ----------
    @staticmethod
    def _is_allowed_import(alias: ast.alias) -> bool:
        # 許可： import numpy / import numpy as np
        return alias.name == "numpy" and (alias.asname in (None, "np"))

    @staticmethod
    def _is_allowed_from_import(node: ast.ImportFrom) -> bool:
        # 許可： from manim import * だけでなく、from manim import Scene, VGroup ... も許可
        return node.level == 0 and node.module == "manim"

    # ---------- import ----------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_full = alias.name
            asname = alias.asname
            if not self._is_allowed_import(alias):
                shown = f"import {mod_full}" + (f" as {asname}" if asname else "")
                self.findings.append(
                    (
                        node.lineno,
                        f"disallowed import: `{shown}` "
                        f"(allowed only: `from manim import *` / `from manim import X,...`, `import numpy as np`, `import numpy`)",
                    )
                )
            else:
                self.module_alias[asname or mod_full] = "numpy"
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # 相対 import は常に NG
        if node.level and node.level > 0:
            self.findings.append((node.lineno, "disallowed relative import (allowed only: from manim import ...)"))
            self.generic_visit(node)
            return

        if not self._is_allowed_from_import(node):
            shown_names = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in node.names)
            self.findings.append(
                (
                    node.lineno,
                    f"disallowed from-import: `from {node.module} import {shown_names}` "
                    f"(allowed only: from manim import ...)",
                )
            )
        self.generic_visit(node)

    # ---------- 代入経由の関数エイリアス ----------
    def visit_Assign(self, node: ast.Assign) -> None:
        fqn = self._resolve_fqn(node.value)
        # __builtins__['eval'] などの検知（かつ束縛にも反映）
        self._check_subscript_builtins(node.value, node.lineno, assign_targets=node.targets)

        if fqn:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.name_bindings[tgt.id] = fqn
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and isinstance(node.target, ast.Name):
            fqn = self._resolve_fqn(node.value)
            self._check_subscript_builtins(node.value, node.lineno, assign_targets=[node.target])
            if fqn:
                self.name_bindings[node.target.id] = fqn
        self.generic_visit(node)

    # ---------- 危険なダンダー属性そのものの参照 ----------
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in SUSPICIOUS_DUNDERS:
            self.findings.append((node.lineno, f"suspicious dunder attribute: `{node.attr}`"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "__builtins__":
            self.findings.append((node.lineno, "suspicious name: `__builtins__`"))
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # 例: __builtins__['open'] / f.__globals__['__builtins__']['eval'] / globals()['exec']
        self._check_subscript_builtins(node, node.lineno)
        self.generic_visit(node)

    # ---------- FQN 解決（Name/Attribute/既知束縛/モジュールエイリアス） ----------
    def _resolve_fqn(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            # 代入束縛を最優先
            if node.id in self.name_bindings:
                return self.name_bindings[node.id]
            # builtins の危険関数名（素の識別子）を FQN 化
            if node.id in {"eval", "exec", "compile", "__import__", "getattr", "globals", "locals", "vars", "dir"}:
                return f"builtins.{node.id}"
            if node.id == "open":
                return "builtins.open"
            # モジュールエイリアス（np -> numpy）
            if node.id in self.module_alias:
                return self.module_alias[node.id]
            return node.id

        # Attribute（再帰的にベースを解決）
        if isinstance(node, ast.Attribute):
            base = self._resolve_fqn(node.value)
            if base is None:
                return None
            return f"{base}.{node.attr}"

        # Subscript 等は解決しない（呼び出し側で別途判定）
        return None

    # __builtins__ / __globals__ / __dict__ から危険キーを引く Subscript を検出
    def _check_subscript_builtins(
        self, node: ast.AST, lineno: int, assign_targets: Optional[List[ast.expr]] = None
    ) -> None:
        # __builtins__/__globals__/__dict__ などのコンテナから危険キーを引くパターンを検出
        def is_suspicious_container(n: ast.AST) -> bool:
            if isinstance(n, ast.Name) and n.id == "__builtins__":
                return True
            if isinstance(n, ast.Attribute) and n.attr in {"__globals__", "__dict__"}:
                return True
            if isinstance(n, ast.Subscript):
                return is_suspicious_container(n.value)
            if isinstance(n, ast.Attribute):
                return is_suspicious_container(n.value)
            return False

        if not isinstance(node, ast.Subscript):
            return

        # 文字列キー抽出
        key = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value

        # 1) __builtins__/__globals__/__dict__ 経由で危険キー → 即 NG
        if is_suspicious_container(node.value) and key in DANGEROUS_BUILTIN_KEYS:
            self.findings.append((lineno, f"dangerous builtin via subscript: `{key}`"))

        # 2) Subscript 由来の束縛は taint（後で call したら NG）
        if assign_targets:
            for tgt in assign_targets:
                if isinstance(tgt, ast.Name):
                    self.tainted_from_subscript.add(tgt.id)

    # ---------- 呼び出し検査 ----------
    def visit_Call(self, node: ast.Call) -> None:
        # 関数が Subscript で取り出されている（例: danger["f"](...)）→ 一律 NG
        if isinstance(node.func, ast.Subscript):
            self.findings.append((node.lineno, "call via Subscript is disallowed"))

        # Subscript 由来で taint された別名からの呼び出しも NG
        if isinstance(node.func, ast.Name) and node.func.id in self.tainted_from_subscript:
            self.findings.append((node.lineno, "call via subscript-derived alias is disallowed"))

        fqn = self._resolve_fqn(node.func) or ""

        # 危険 prefix は独立にチェック（numpy.* に限らない）
        for p in BANNED_PREFIXES:
            if fqn.startswith(p + "."):
                # subprocess.* は下の専用ブロックでも検査するが、ここでも記録しておく
                self.findings.append((node.lineno, f"{fqn} detected (banned prefix: {p})"))
                break

        # 直接名での検出（getattr/__import__/globals/locals/vars/dir）
        if isinstance(node.func, ast.Name) and node.func.id in {
            "getattr",
            "__import__",
            "globals",
            "locals",
            "vars",
            "dir",
        }:
            self.findings.append((node.lineno, f"{node.func.id} detected"))

        # FQN 末尾でも検出（builtins.getattr など）
        if (
            fqn.endswith(".getattr")
            or fqn.endswith(".__import__")
            or fqn
            in {
                "builtins.globals",
                "builtins.locals",
                "builtins.vars",
                "builtins.dir",
            }
        ):
            self.findings.append((node.lineno, f"{fqn} detected"))

        # getattr(x, "open") のような第2引数の危険キーも検査
        if fqn.endswith(".getattr") or (isinstance(node.func, ast.Name) and node.func.id == "getattr"):
            if len(node.args) >= 2:
                key = _const_str(node.args[1])
                if key in DANGEROUS_BUILTIN_KEYS:
                    self.findings.append((node.lineno, f"dangerous getattr target: `{key}`"))

        # open / io.open / Path.open はモード問わず NG
        if fqn in {"builtins.open", "io.open"} or fqn.endswith(".open"):
            self.findings.append((node.lineno, "file open detected"))

        # Path ライク / ndarray ライクの I/O 属性
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in PATH_WRITE_METHODS or attr in PATH_READ_METHODS:
                self.findings.append((node.lineno, f"Path-like I/O attr detected: .{attr}"))
            if attr in NDARRAY_IO_ATTRS:
                self.findings.append((node.lineno, f"ndarray-like I/O attr detected: .{attr}"))

        # 危険 FQN は全面禁止（到達可能セットのみ）
        if fqn in BANNED_FQNS:
            self.findings.append((node.lineno, f"{fqn} detected"))

        # NumPy I/O：サブモジュール経由も封じる（suffix）
        if fqn.startswith("numpy."):
            suffix = fqn.split(".")[-1]
            if suffix in NUMPY_IO_SUFFIXES:
                self.findings.append((node.lineno, f"numpy I/O detected: `{fqn}`"))

        # subprocess.* は到達時点で NG。さらに KW（shell/executable）も検査
        if fqn.startswith("subprocess."):
            self.findings.append((node.lineno, f"{fqn} detected (subprocess is not allowed)"))
            for kw in node.keywords or []:
                if kw.arg in SUBPROC_DANGEROUS_KW:
                    self.findings.append((node.lineno, f"subprocess dangerous kw: `{kw.arg}` specified"))

        self.generic_visit(node)


def analyze_code(code: str) -> Tuple[bool, List[Tuple[int, str]]]:
    """
    解析して (安全かどうか, 検出内容のリスト) を返す。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, [(1, "SyntaxError: failed to parse")]
    sg = StrictGuard()
    sg.visit(tree)
    return (len(sg.findings) == 0), sorted(sg.findings, key=lambda x: x[0])


def is_code_safe(code: str) -> bool:
    """
    True: 危険が見当たらない（実行候補）
    False: 危険の可能性あり（実行禁止）
    """
    ok, _ = analyze_code(code)
    return ok
