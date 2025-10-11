# manim_strict_guard.py
"""
厳格ガード方針
- 危険API（os/shutil/subprocess/os.system 等）の使用を **全面禁止**。import しただけで NG。
- エイリアス（import as）/ from-import / 代入による関数参照の伝播を解決して検出。
- 外部コマンドは ffmpeg / ffprobe のみ許可（subprocess.run/Popen/os.system）。
- 書込み/破壊操作（open(...,"w/ x/ a/+"), Path.write_*, Path.unlink/rename/...）は NG。
- メタ実行（eval/exec/compile/__import__/importlib.import_module）は NG。
- getattr で文字列名を参照して実行しそうなコードは NG（保守的判定）。
- SyntaxError など解析不能は NG。
"""

import ast
from typing import List, Tuple, Optional, Dict, Set

# --- 外部コマンドのホワイトリスト ---
ALLOWED_SUBPROCESS_BASENAMES: Set[str] = {"ffmpeg", "ffprobe"}

# --- モジュール import しただけで NG（厳格） ---
BANNED_IMPORT_MODULES: Set[str] = {
    "os",
    "shutil",
    "subprocess",
    "ctypes",
    "importlib",
    # 必要に応じて追加
}

# --- 完全修飾名で NG な関数/メソッド ---
BANNED_FQNS: Set[str] = {
    # os
    "os.remove", "os.unlink", "os.rmdir", "os.removedirs",
    "os.rename", "os.replace", "os.system",
    # shutil
    "shutil.rmtree", "shutil.move", "shutil.copy", "shutil.copy2",
    "shutil.copyfile", "shutil.copytree",
    # subprocess
    "subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
    "subprocess.check_output",
    # メタ実行
    "builtins.eval", "builtins.exec", "builtins.compile",
    "__import__", "importlib.import_module",
}

# --- 名前ベース（レシーバ不明でも NG にする破壊的メソッド名） ---
DESTRUCTIVE_ATTR_NAMES: Set[str] = {
    "remove", "unlink", "rename", "replace", "rmdir", "rmtree", "move",
}

# --- Path 書込みメソッド名 ---
PATH_WRITE_METHODS: Set[str] = {"write_text", "write_bytes"}

# --- open の書込みモードトークン ---
WRITE_MODE_TOKENS = ("w", "x", "a", "+")


def _const_str(n: ast.AST) -> Optional[str]:
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None


class StrictGuard(ast.NodeVisitor):
    """
    - import/alias/代入を辿るライトな名前解決で「危険APIの使用を全面禁止」。
    - 何か判断に迷えば NG を追加（厳格）。
    """
    def __init__(self) -> None:
        self.findings: List[Tuple[int, str]] = []
        # as エイリアス（モジュール名解決）
        self.module_alias: Dict[str, str] = {}   # {"sh": "shutil"}
        # from-import の関数/属性完全修飾名
        self.func_alias: Dict[str, str] = {}     # {"rm": "shutil.rmtree"}
        # 代入された参照の簡易解決（f = shutil.rmtree / g = subprocess.run など）
        self.name_bindings: Dict[str, str] = {}  # {"f": "shutil.rmtree"}
        # Path エイリアス
        self.path_alias: Set[str] = set()

    # ---------- import ----------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_full = alias.name  # "os.path"
            top = mod_full.split(".", 1)[0]  # "os"
            asname = alias.asname or alias.name
            self.module_alias[asname] = mod_full
            if top in BANNED_IMPORT_MODULES:
                self.findings.append((node.lineno, f"banned import: {mod_full}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module:
            return
        top = node.module.split(".", 1)[0]
        for alias in node.names:
            asname = alias.asname or alias.name
            fqn = f"{node.module}.{alias.name}"
            self.func_alias[asname] = fqn
            if top in BANNED_IMPORT_MODULES:
                self.findings.append((node.lineno, f"banned from-import: {fqn}"))
            if node.module == "pathlib" and alias.name == "Path":
                self.path_alias.add(asname)
        self.generic_visit(node)

    # ---------- 代入経由の関数エイリアス ----------
    def visit_Assign(self, node: ast.Assign) -> None:
        # 右辺が関数参照（Name/Attribute）なら、左辺 Name に FQN を束縛
        fqn = self._resolve_fqn(node.value)
        if fqn:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.name_bindings[tgt.id] = fqn
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and isinstance(node.target, ast.Name):
            fqn = self._resolve_fqn(node.value)
            if fqn:
                self.name_bindings[node.target.id] = fqn
        self.generic_visit(node)

    # ---------- FQN 解決（Name/Attribute/既知束縛のみ） ----------
    def _resolve_fqn(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            # 代入で覚えていればそれを返す
            if node.id in self.name_bindings:
                return self.name_bindings[node.id]
            # from-import で覚えていればそれを返す
            if node.id in self.func_alias:
                return self.func_alias[node.id]
            # builtins/メタ実行
            if node.id in {"eval", "exec", "compile", "__import__"}:
                return f"builtins.{node.id}" if node.id != "__import__" else "__import__"
            if node.id == "open":
                return "builtins.open"
            return node.id

        if isinstance(node, ast.Attribute):
            parts = []
            cur = node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                base_raw = self.module_alias.get(cur.id, cur.id)  # as解決
                parts.append(base_raw)
                parts.reverse()
                return ".".join(parts)
        return None

    # ---------- open の書込みモード ----------
    def _is_write_mode(self, call: ast.Call) -> bool:
        mode = None
        if len(call.args) >= 2:
            mode = _const_str(call.args[1])
        for kw in call.keywords or []:
            if kw.arg == "mode":
                mode = _const_str(kw.value) or mode
        return bool(mode) and any(tok in mode for tok in WRITE_MODE_TOKENS)

    # ---------- 外部コマンドの許可判定（ffmpeg/ffprobe のみ） ----------
    def _subprocess_danger(self, call: ast.Call, fqn: str) -> bool:
        # shell=True は無条件危険
        for kw in call.keywords or []:
            if kw.arg == "shell":
                return True

        if not call.args:
            return True

        arg0 = call.args[0]

        def head_basename_from_string(s: str) -> str:
            head = s.strip().split()[0]
            head = head.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            head = head.split(".", 1)[0].lower()
            return head

        # os.system は常に文字列コマンド
        if fqn == "os.system":
            s = _const_str(arg0)
            if not s:
                return True
            return head_basename_from_string(s) not in ALLOWED_SUBPROCESS_BASENAMES

        # subprocess.* は list/tuple の先頭 or 文字列の先頭トークンを見る
        if isinstance(arg0, (ast.List, ast.Tuple)):
            if not arg0.elts:
                return True
            head_lit = _const_str(arg0.elts[0])
            if not head_lit:
                return True
            return head_basename_from_string(head_lit) not in ALLOWED_SUBPROCESS_BASENAMES
        else:
            s = _const_str(arg0)
            if s:
                return head_basename_from_string(s) not in ALLOWED_SUBPROCESS_BASENAMES
            return True  # 変数などは不明 → 危険

    # ---------- getattr/動的実行まがいは NG ----------
    def visit_Call(self, node: ast.Call) -> None:
        # getattr(obj, "name") や __import__ などは危険（実行面を想定）
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            self.findings.append((node.lineno, "dynamic getattr call detected"))
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            self.findings.append((node.lineno, "__import__ detected"))

        fqn = self._resolve_fqn(node.func) or ""

        # open / io.open / Path.open の書込み
        if fqn in {"builtins.open", "io.open"} or fqn.endswith(".open"):
            if self._is_write_mode(node):
                self.findings.append((node.lineno, "write-open detected"))

        # 属性名だけで破壊系をブロック（受け手不明でも NG）
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in DESTRUCTIVE_ATTR_NAMES:
                self.findings.append((node.lineno, f"destructive attr call: {attr}"))
            if attr in PATH_WRITE_METHODS:
                self.findings.append((node.lineno, f"Path.{attr} detected"))

        # 危険 FQN は全面禁止（subprocess は別途コマンドも検査）
        if fqn in BANNED_FQNS:
            if fqn in {"subprocess.run", "subprocess.Popen", "subprocess.call",
                       "subprocess.check_call", "subprocess.check_output", "os.system"}:
                if self._subprocess_danger(node, fqn):
                    self.findings.append((node.lineno, f"{fqn} dangerous"))
            else:
                self.findings.append((node.lineno, f"{fqn} detected"))

        self.generic_visit(node)


def is_code_safe(code: str) -> bool:
    """
    True: 危険が見当たらない（実行候補）
    False: 危険の可能性あり（実行禁止）
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False  # 解析不能は危険扱い
    sg = StrictGuard()
    sg.visit(tree)
    return len(sg.findings) == 0


def reasons(code: str) -> List[Tuple[int, str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [(-1, f"SyntaxError: {e}")]
    sg = StrictGuard()
    sg.visit(tree)
    return sg.findings


# CLI 例
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # 引数にファイルパスが来た場合
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            src = f.read()
    else:
        # リダイレクトやパイプ時は標準入力を全部読む
        src = sys.stdin.read()
    ok = is_code_safe(src)
    
    if not ok:
        for ln, msg in reasons(src):
            print(f" L{ln}: {msg}")
    else:
        print("No problems found.")
