import re
from typing import Any, Dict, List, Optional, Tuple


class DiffApplyError(Exception):
    """（エラー）unified diff をスクリプトへ適用できなかったときに投げる例外。"""

    # 例：差分が空／ハンクが1つも当たらない 等


class DiffPatcher:
    """
    LLM などが返す「差分パッチ」や「丸ごとのコード」を、
    できるだけ安全に元スクリプトへ反映するためのヘルパー。

    フロー概要：
      1) 応答から diff ブロック（```diff ...``` / *** Begin Patch ... ***）を抽出
      2) unified diff をハンクへ分解し、行の"完全一致"によるパターンマッチで適用
         - 行番号はほとんどずれて返ってくるため "探索ウィンドウの目安" として扱う
      3) いずれでもなければ、元スクリプトをそのまま返す（安全側）
    """

    def __init__(self, logger=None):
        self.logger = logger

    # ---------- Logging helpers ----------
    def _debug(self, message: str) -> None:
        if self.logger:
            self.logger.debug(message)

    def _info(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _warning(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)

    def _error(self, message: str) -> None:
        if self.logger:
            self.logger.error(message)

    # ---------- Cleaners / Extractors ----------
    @staticmethod
    def _extract_diff_block(response_text: str) -> Optional[str]:
        """
        LLM 応答から diff ブロックのみを抽出する。
        対応形式：
          - ```diff / ```patch / ```unidiff のコードフェンス
          - *** Begin Patch ～ *** End Patch の囲み
        """
        if not response_text:
            return None

        # ```diff / patch / unidiff``` のコードブロック検出
        code_block_pattern = re.compile(
            r"```(?:diff(?:-fenced)?|patch|unidiff)\s*\n([\s\S]*?)```",
            flags=re.IGNORECASE,
        )
        match = code_block_pattern.search(response_text)
        if match:
            return match.group(1).strip()

        # *** Begin Patch ～ *** End Patch の囲み（LLM がよく使う装飾）
        begin_idx = response_text.find("*** Begin Patch")
        end_idx = response_text.find("*** End Patch")
        if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
            return response_text[begin_idx : end_idx + len("*** End Patch")].strip()
        return None

    @staticmethod
    def _sanitize_patch_text(diff_text: str) -> str:
        """
        diff テキストから装飾行（*** Begin/End Patch、*** Update File 等）を落とす。
        実際の unified diff 部分だけを残すための前処理。
        """
        sanitized_lines = []
        for line in diff_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("*** Begin Patch") or stripped.startswith("*** End Patch"):
                continue
            if stripped.startswith("*** Update File"):
                continue
            sanitized_lines.append(line)
        return "\n".join(sanitized_lines).strip()

    @staticmethod
    def _normalize_newlines(text: str) -> str:
        """
        改行表現の正規化（CRLF/CR → LF へ）と BOM 除去。
        diff/スクリプト双方の比較を安定化させる。
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.lstrip("\ufeff")
        return text

    # ---------- Diff Parsing (manual) ----------

    def _parse_unified_diff_to_hunks(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        unified diff テキスト（複数ファイル・複数ハンク可）を、
        構造化された "ハンク" の配列へ変換する。

        ハンクとは：
          @@ -<src_start>,<src_len> +<dst_start>,<dst_len> @@
          に続く "+/-/ 空白" の行ブロック（追加/削除/コンテキスト）のこと。
        """
        text = self._normalize_newlines(diff_text)

        file_from = None  # --- a/xxx に対応（今は参照のみ）
        file_to = None  # +++ b/xxx に対応（今は参照のみ）

        hunks: List[Dict[str, Any]] = []
        current_hunk: Optional[Dict[str, Any]] = None

        # ハンクヘッダ（@@ -a,b +c,d @@）を拾う正規表現
        hunk_re = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@.*$")

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # ファイルヘッダ（--- / +++）は取り出して保持だけしておく
            if line.startswith("--- "):
                file_from = line[4:].strip()
                i += 1
                continue
            if line.startswith("+++ "):
                file_to = line[4:].strip()
                i += 1
                continue

            # ハンクヘッダを検出
            m = hunk_re.match(line)
            if m:
                # 直前のハンクを締めて保存
                if current_hunk is not None:
                    self._finalize_hunk(current_hunk)
                    hunks.append(current_hunk)

                source_start = int(m.group(1))
                source_len = int(m.group(2) or "1")
                target_start = int(m.group(3))
                target_len = int(m.group(4) or "1")

                # 新しいハンクの器を作成
                current_hunk = {
                    "source_start": source_start,
                    "source_len": source_len,
                    "target_start": target_start,
                    "target_len": target_len,
                    "lines": [],  # ("+/-/ ", 行文字列) のタプル列
                    "file_from": file_from,
                    "file_to": file_to,
                }
                i += 1

                # ハンク本体（+/-/空白行）を読み取る
                while i < len(lines):
                    body_line = lines[i]
                    # 次のハンクヘッダが来たら本体終わり
                    if hunk_re.match(body_line):
                        break
                    # "No newline at end of file" 行は無視
                    if body_line.startswith("\\ No newline at end of file"):
                        i += 1
                        continue
                    # 空行（""）は "コンテキスト行" とみなす
                    if body_line.startswith((" ", "+", "-")) or body_line == "":
                        if body_line == "":
                            current_hunk["lines"].append((" ", ""))
                        else:
                            current_hunk["lines"].append((body_line[0], body_line[1:]))
                        i += 1
                        continue
                    # それ以外の行が来たらハンク本体終了
                    break
                continue

            # 何も該当しなければ次の行へ
            i += 1

        # 末尾ハンクの締め処理
        if current_hunk is not None:
            self._finalize_hunk(current_hunk)
            hunks.append(current_hunk)

        return hunks

    @staticmethod
    def _finalize_hunk(hunk: Dict[str, Any]) -> None:
        """
        ハンクに対して、適用に使う補助配列を作る。
          - from_lines: "削除＋コンテキスト"（= 置き換え対象に一致させる元の並び）
          - to_lines  : "追加＋コンテキスト"（= 置き換え後の並び）
        """
        body = hunk.get("lines", [])
        from_lines: List[str] = []
        to_lines: List[str] = []

        # "空白/削除" は from_lines に、"空白/追加" は to_lines に入れる
        for tag, content in body:
            if tag in (" ", "-"):
                from_lines.append(content)
            if tag in (" ", "+"):
                to_lines.append(content)

        hunk["from_lines"] = from_lines
        hunk["to_lines"] = to_lines

    # ---------- Pattern Matching Engine ----------
    @staticmethod
    def _find_all_subsequence(
        haystack: List[str],
        needle: List[str],
        start: int = 0,
        end: Optional[int] = None,
    ) -> List[int]:
        """
        連続部分列 needle が一致するすべての開始位置を返す（重なりなし進行）。
        """
        if end is None:
            end = len(haystack)
        n = len(needle)
        idxs: List[int] = []
        if n == 0:
            return [start]
        i = max(start, 0)
        while i + n <= end:
            ok = True
            for j in range(n):
                if haystack[i + j] != needle[j]:
                    ok = False
                    break
            if ok:
                idxs.append(i)
                i += n if n > 0 else 1
            else:
                i += 1
        return idxs

    def _apply_hunk_within_window(
        self,
        lines: List[str],
        hunk: Dict[str, Any],
        window_start: int,
        window_end: int,
    ) -> Tuple[bool, List[str]]:
        """
        指定ウィンドウ内で from_lines を探して置換。
        成功： (True, 置換後行列) / 失敗： (False, 元の行列)

        追加のみ（from_lines が空）の場合は、ウィンドウ中央へ挿入する。
        マッチが複数ある場合は警告ログを出し、ウィンドウ中央に最も近い候補を採用する。
        一致位置 pos は debug ログに出す。
        """
        src = hunk["from_lines"]
        dst = hunk["to_lines"]

        # ウィンドウ中央（優先探索の基準点）
        center = (window_start + window_end) // 2

        # 1) "追加だけ"のハンク（アンカーなし）はウィンドウ中央へ挿入
        if len(src) == 0:
            pos = max(window_start, min(center, window_end))
            self._warning(f"   [~] Hunk has empty from_lines; inserting at {pos} (window {window_start}:{window_end}).")
            new_lines = lines[:pos] + dst + lines[pos:]
            return True, new_lines

        # 2) ウィンドウ内探索：複数候補があるかチェック
        cands = self._find_all_subsequence(lines, src, start=window_start, end=window_end)
        pos = -1
        if len(cands) > 1:
            chosen = min(cands, key=lambda p: abs(p - center))
            self._warning(
                f"   [~] Multiple matches in window {window_start}:{window_end}; "
                f"chosen {chosen}, candidates={cands[:8]}"
            )
            pos = chosen
        elif len(cands) == 1:
            pos = cands[0]

        if pos != -1:
            self._debug(f"   [+] Matched at {pos}..{pos + len(src)} (window {window_start}:{window_end}).")
            new_lines = lines[:pos] + dst + lines[pos + len(src) :]
            return True, new_lines

        return False, lines

    def _apply_diff_by_pattern(self, original_script: str, diff_text: str) -> Tuple[str, int, int]:
        """
        ハンクを上から順に"最良努力"で適用していく本体。
        戻り値: (更新後スクリプト, 適用できたハンク数, 総ハンク数)
        """
        if not diff_text.strip():
            raise DiffApplyError("Empty diff content.")

        text = self._normalize_newlines(diff_text.strip("\n"))
        hunks = self._parse_unified_diff_to_hunks(text)
        if not hunks:
            raise DiffApplyError("No hunks detected in diff.")

        # 末尾改行の有無を保持（結合後に復元するため）
        orig_has_trailing_nl = original_script.endswith("\n")
        lines = original_script.splitlines()

        applied = 0
        total = len(hunks)

        for idx, h in enumerate(hunks):
            # 行番号は目安。そこを中心に広めの探索ウィンドウを張る。
            source_start = h.get("source_start")
            src_len = len(h.get("from_lines", [])) or 1

            if source_start and source_start > 0:
                # ウィンドウ半径：最低 200 行、変更サイズにも比例させて余裕を見る
                radius = max(200, src_len * 4 + 50)
                center = max(0, source_start - 1)  # diff は 1-index のため -1
                w_start = max(0, center - radius)
                w_end = min(len(lines), center + radius)
            else:
                # 行番号情報なし → 全体をウィンドウに
                w_start, w_end = 0, len(lines)

            ok, new_lines = self._apply_hunk_within_window(lines, h, w_start, w_end)
            if ok:
                applied += 1
                lines = new_lines
                self._debug(f"   [+] Hunk {idx + 1}/{total} applied (window {w_start}:{w_end}).")
            else:
                # 当てられないハンクは飛ばす（部分適用は許容）
                self._warning(f"   [=] Hunk {idx + 1}/{total} could not be matched; skipping.")

        updated_script = "\n".join(lines)
        # もともと末尾改行があれば維持
        if orig_has_trailing_nl and not updated_script.endswith("\n"):
            updated_script += "\n"

        return updated_script, applied, total

    def _apply_unified_diff(self, original_script: str, diff_text: str) -> str:
        """
        外向けの"diff 適用"API（互換性保持）。
        1 つもハンクが当たらなければ DiffApplyError を投げる。
        """
        updated, applied, total = self._apply_diff_by_pattern(original_script, diff_text)
        if applied == 0:
            raise DiffApplyError("No hunks could be applied.")
        self._info(f"   [+] Applied {applied}/{total} hunk(s) successfully.")
        return updated

    def process_edit_response(self, *, original_script: str, llm_response: str) -> str:
        """
        LLM 応答を受け取り、まずは diff 適用を試す。
        それが無理なら元スクリプトを返す。
        """
        response_text = llm_response.strip()

        # 1) diff ブロック抽出 → 前処理 → 適用
        diff_block = self._extract_diff_block(response_text)
        if diff_block:
            sanitized_diff = self._sanitize_patch_text(diff_block)
            try:
                updated = self._apply_unified_diff(original_script, sanitized_diff)
                self._debug("   [+] Applied diff-fenced patch successfully.")
                return updated
            except DiffApplyError as exc:
                # diff は失敗
                self._error(f"   [-] Failed to apply diff patch: {exc}. ")

        # 2) diff 適用失敗 or diff ブロックなし → 元スクリプトを返す
        self._warning("   [-] No valid diff or script detected. Keeping original script.")
        return original_script


__all__ = ["DiffPatcher", "DiffApplyError"]
