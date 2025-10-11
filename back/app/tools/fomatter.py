import re, ast, html

CODEBLOCK_RE = re.compile(
    r"```(?:\s*python)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE
)

def sanitize_python_code(raw: str) -> str:
    """
    - ```python ... ``` / ``` ... ``` の最長ブロックを抽出
    - ブロックが無ければ raw をそのまま使う
    - HTML エスケープが紛れた場合 (&lt; 等) を復元
    - 改行・BOM・末尾空白などの正規化
    """
    if raw is None:
        return ""
    text = raw.strip()

    # HTMLエスケープの解除（LLMによっては混ざる）
    text = html.unescape(text)

    blocks = CODEBLOCK_RE.findall(text)
    if blocks:
        # 複数ある場合は最長を採用（途中説明が混在する出力を想定）
        code = max(blocks, key=len)
    else:
        # フェンス無い場合は、そのまま（が、念のため先頭・末尾の ``` を落とす）
        code = re.sub(r"^```(?:\s*python)?\s*|```$", "", text, flags=re.IGNORECASE).strip()

    # 先頭BOMや奇妙な不可視文字の除去
    code = code.lstrip("\ufeff").strip()

    # 余計なバックティックの取りこぼし対策（行頭/行末）
    code = re.sub(r"^\s*```\s*$", "", code, flags=re.MULTILINE).strip()

    # 最低限の構文チェック（ここで落ちたら上位で再生成・修正へ）
    try:
        ast.parse(code)
    except SyntaxError:
        # 例: コードフェンス除去に失敗 or 説明文優勢だった場合 → raw 全体からも最後の対処
        # それでもダメなら上位で LLM 修正に回す
        pass

    return code
