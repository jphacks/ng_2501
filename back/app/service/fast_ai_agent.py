import re
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

# LangGraphのコンポーネント
from typing import TypedDict, Literal, Optional, List, Tuple, Dict, Any

from app.service.base_agent import BaseManimAgent


class DiffApplyError(Exception):
    """Raised when a unified diff cannot be applied to the script."""


class ManimGraphState(TypedDict):
    """
    グラフ全体で引き回す状態。
    """

    # --- 初期入力 ---
    user_request: str  # `content` (構造化説明)
    generation_instructions: str  # `enhance_prompt` (動画の指示)
    animation_plan: str  # 生成されたアニメーションプラン
    video_id: str  # `video_id` (ファイル名用)

    # --- 変化する状態 ---
    current_script: str  # 現在のManimスクリプト (修正対象)
    last_error: str  # 最後に発生したエラーメッセージ (LinterまたはRuntime)
    error_type: Literal["", "lint", "runtime"]  # エラーの種別
    is_bad_request: bool  # 不正リクエストフラグ

    # --- 制御用 ---
    max_retries: int  # 最大試行回数 (元の max_loop)
    current_retry: int  # 現在の試行回数 (元の loop)
    mode: Literal["generate", "edit"]  # 動作モード


class ManimFastAnimationService(BaseManimAgent):
    def __init__(self, prompt_path="prompt/fast_ai_prompts.toml"):
        super().__init__(prompt_path)
        # --- LangGraph のグラフを構築 ---
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    # ============================================================
    # ==========   Internal helpers for diff-based editing  =======
    # ============================================================

    # ---------- Cleaners / Extractors ----------

    def _strip_code_fence(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return cleaned
        fence_match = re.match(
            r"```(?:\w+)?\s*\n([\s\S]*?)```", cleaned, flags=re.IGNORECASE
        )
        if fence_match:
            return fence_match.group(1).strip()
        return cleaned

    def _extract_diff_block(self, response_text: str) -> Optional[str]:
        """
        LLM出力から diff コードブロックまたは *** Begin/End Patch *** ブロックを抽出。
        """
        if not response_text:
            return None
        code_block_pattern = re.compile(
            r"```(?:diff(?:-fenced)?|patch|unidiff)\s*\n([\s\S]*?)```",
            flags=re.IGNORECASE,
        )
        match = code_block_pattern.search(response_text)
        if match:
            return match.group(1).strip()

        begin_idx = response_text.find("*** Begin Patch")
        end_idx = response_text.find("*** End Patch")
        if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
            return response_text[begin_idx : end_idx + len("*** End Patch")].strip()
        return None

    def _sanitize_patch_text(self, diff_text: str) -> str:
        """
        LLMが出す飾り行（*** Begin Patch等）やメタ行を除去。
        """
        sanitized_lines = []
        for line in diff_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("*** Begin Patch") or stripped.startswith(
                "*** End Patch"
            ):
                continue
            if stripped.startswith("*** Update File"):
                continue
            sanitized_lines.append(line)
        return "\n".join(sanitized_lines).strip()

    @staticmethod
    def _normalize_newlines(text: str) -> str:
        # BOM/CRLF/CR を正規化
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.lstrip("\ufeff")
        return text

    @staticmethod
    def _strip_line_ending(value: str) -> str:
        if value.endswith("\r\n"):
            return value[:-2]
        if value.endswith("\n"):
            return value[:-1]
        return value

    # ---------- Diff Parsing (manual) ----------

    def _parse_unified_diff_to_hunks(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        Unified Diff（1ファイル以上、複数ハンク可）を手書きで解析してハンク配列へ。
        - ファイル名や行番号は「補助的に」保持（信頼しない）。
        - ハンクの本文は ' ' / '-' / '+' から始まる行のみ扱う。
        - '\\ No newline at end of file' は無視。
        戻り値: List[{
           "source_start": Optional[int],
           "source_len": Optional[int],
           "target_start": Optional[int],
           "target_len": Optional[int],
           "lines": List[Tuple[str, str]],  # (tag, line_content)
           "from_lines": List[str],         # ' ' と '-' の行の本文
           "to_lines": List[str],           # ' ' と '+' の行の本文
           "lead_ctx": List[str],           # 先頭連続コンテキスト
           "tail_ctx": List[str],           # 末尾連続コンテキスト
           "file_from": Optional[str],
           "file_to": Optional[str],
        }]
        """
        text = self._normalize_newlines(diff_text)

        # ファイルヘッダは補助的に抜き出すが、適用には使わない
        file_from = None
        file_to = None

        hunks: List[Dict[str, Any]] = []
        current_hunk: Optional[Dict[str, Any]] = None

        # ハンクヘッダの正規表現
        # 例: @@ -138,3 +138,3 @@ 任意のコメント
        hunk_re = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@.*$")

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # ファイルヘッダ（補助）
            if line.startswith("--- "):
                file_from = line[4:].strip()
                i += 1
                continue
            if line.startswith("+++ "):
                file_to = line[4:].strip()
                i += 1
                continue

            # ハンク開始
            m = hunk_re.match(line)
            if m:
                # 進行中のハンクがあれば閉じる
                if current_hunk is not None:
                    self._finalize_hunk(current_hunk)
                    hunks.append(current_hunk)

                source_start = int(m.group(1))
                source_len = int(m.group(2) or "0")
                target_start = int(m.group(3))
                target_len = int(m.group(4) or "0")

                current_hunk = {
                    "source_start": source_start,
                    "source_len": source_len,
                    "target_start": target_start,
                    "target_len": target_len,
                    "lines": [],
                    "file_from": file_from,
                    "file_to": file_to,
                }
                i += 1
                # ハンク本文を収集
                while i < len(lines):
                    body_line = lines[i]
                    if hunk_re.match(body_line):
                        # 次のハンク開始へ
                        break
                    if body_line.startswith("\\ No newline at end of file"):
                        i += 1
                        continue
                    if body_line.startswith((" ", "+", "-")) or body_line == "":
                        # 空行（""）はタグが無いので、できるだけ安全側で扱う。
                        # ここでは「コンテキスト空行」と見なして ' ' を付与する。
                        if body_line == "":
                            current_hunk["lines"].append((" ", ""))
                        else:
                            current_hunk["lines"].append((body_line[0], body_line[1:]))
                        i += 1
                        continue
                    # タグ無しの行が混入していれば安全のためハンク終了とみなす
                    break
                continue

            # その他の行はスキップ
            i += 1

        # 最後のハンクを確定
        if current_hunk is not None:
            self._finalize_hunk(current_hunk)
            hunks.append(current_hunk)

        return hunks

    def _finalize_hunk(self, hunk: Dict[str, Any]) -> None:
        """
        ハンクの派生情報を作る:
        - from_lines: ' 'と'-'から作るソース側の連結ブロック
        - to_lines:   ' 'と'+'から作るターゲット側の連結ブロック
        - lead_ctx, tail_ctx: 先頭/末尾の連続 ' ' 行
        """
        body = hunk.get("lines", [])
        from_lines: List[str] = []
        to_lines: List[str] = []

        for tag, content in body:
            if tag in (" ", "-"):
                from_lines.append(content)
            if tag in (" ", "+"):
                to_lines.append(content)

        # 先頭連続 ' ' 行
        lead_ctx: List[str] = []
        for tag, content in body:
            if tag == " ":
                lead_ctx.append(content)
            else:
                break

        # 末尾連続 ' ' 行
        tail_ctx: List[str] = []
        for tag, content in reversed(body):
            if tag == " ":
                tail_ctx.insert(0, content)
            else:
                break

        hunk["from_lines"] = from_lines
        hunk["to_lines"] = to_lines
        hunk["lead_ctx"] = lead_ctx
        hunk["tail_ctx"] = tail_ctx

    # ---------- Pattern Matching Engine ----------

    @staticmethod
    def _find_subsequence(
        haystack: List[str],
        needle: List[str],
        start: int = 0,
        end: Optional[int] = None,
    ) -> int:
        """
        haystack 内で needle（連続部分列）と完全一致する最初の開始位置を返す。見つからなければ -1。
        """
        if end is None:
            end = len(haystack)
        n = len(needle)
        if n == 0:
            return start
        limit = max(start, 0)
        while limit + n <= end:
            ok = True
            for j in range(n):
                if haystack[limit + j] != needle[j]:
                    ok = False
                    break
            if ok:
                return limit
            limit += 1
        return -1

    @staticmethod
    def _find_all_subsequence(
        haystack: List[str],
        needle: List[str],
        start: int = 0,
        end: Optional[int] = None,
    ) -> List[int]:
        """
        haystack 内で needle と一致する全ての開始位置を返す。
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

    def _find_subsequence_centered(
        self,
        haystack: List[str],
        needle: List[str],
        center: int,
        start: int,
        end: int,
    ) -> int:
        n = len(needle)
        if n == 0:
            return start
        start = max(start, 0)
        end = min(end, len(haystack))
        candidates: List[int] = []
        i = start
        while i + n <= end:
            if haystack[i : i + n] == needle:
                candidates.append(i)
            i += 1
        if not candidates:
            return -1
        # 中心に最も近い位置を選ぶ
        return min(candidates, key=lambda p: abs(p - center))

    def _apply_hunk_within_window(
        self,
        lines: List[str],
        hunk: Dict[str, Any],
        window_start: int,
        window_end: int,
    ) -> Tuple[bool, List[str]]:
        src = hunk["from_lines"]
        dst = hunk["to_lines"]
        lead = hunk["lead_ctx"]
        tail = hunk["tail_ctx"]

        # ウィンドウ中心（行番号が怪しくても「近辺」を優先）
        center = (window_start + window_end) // 2

        # 1) 中心優先の完全一致
        pos = self._find_subsequence_centered(
            lines, src, center, start=window_start, end=window_end
        )
        if pos != -1:
            new_lines = lines[:pos] + dst + lines[pos + len(src) :]
            return True, new_lines

        # 2) 先頭アンカー（中心に近い候補から試す）
        # if lead:
        #     cand_starts = self._find_all_subsequence(
        #         lines, lead, start=window_start, end=window_end
        #     )
        #     for head_pos in sorted(cand_starts, key=lambda p: abs(p - center)):
        #         start_pos = head_pos
        #         if start_pos + len(src) <= len(lines):
        #             if lines[start_pos : start_pos + len(src)] == src:
        #                 new_lines = (
        #                     lines[:start_pos] + dst + lines[start_pos + len(src) :]
        #                 )
        #                 return True, new_lines

        # 3) 末尾アンカー（中心に近い候補から試す）
        # if tail:
        #     cand_tails = self._find_all_subsequence(
        #         lines, tail, start=window_start, end=window_end
        #     )
        #     for tail_pos in sorted(cand_tails, key=lambda p: abs(p - center)):
        #         start_pos = tail_pos - (len(src) - len(tail))
        #         if start_pos < window_start or start_pos < 0:
        #             continue
        #         if start_pos + len(src) <= len(lines):
        #             if lines[start_pos : start_pos + len(src)] == src:
        #                 new_lines = (
        #                     lines[:start_pos] + dst + lines[start_pos + len(src) :]
        #                 )
        #                 return True, new_lines

        # 4) 全体で中心優先の最後の完全一致
        pos_global = self._find_subsequence_centered(
            lines, src, center=(len(lines) // 2), start=0, end=len(lines)
        )
        if pos_global != -1:
            new_lines = lines[:pos_global] + dst + lines[pos_global + len(src) :]
            return True, new_lines

        return False, lines

    def _apply_diff_by_pattern(
        self, original_script: str, diff_text: str
    ) -> Tuple[str, int, int]:
        """
        手書きパーサで得たハンクを、範囲内パターンマッチで順次適用する。
        - 行番号は補助的にウィンドウ中心のヒントとしてのみ使用。
        - 1つでも適用できれば結果を採用。0なら失敗扱い。
        戻り値: (updated_script, applied_count, total_hunks)
        """
        if not diff_text.strip():
            raise DiffApplyError("Empty diff content.")

        text = self._normalize_newlines(diff_text.strip("\n"))
        hunks = self._parse_unified_diff_to_hunks(text)
        if not hunks:
            raise DiffApplyError("No hunks detected in diff.")

        orig_has_trailing_nl = original_script.endswith("\n")
        lines = original_script.splitlines()

        applied = 0
        total = len(hunks)

        for idx, h in enumerate(hunks):
            # 行番号は不確かなので、広めのウィンドウをヒントに使う（無ければ全体）
            source_start = h.get("source_start")  # 1-based or None
            src_len = len(h.get("from_lines", [])) or 1

            if source_start and source_start > 0:
                # ウィンドウは中心±R。Rはソース長と定数で決める
                radius = max(200, src_len * 4 + 50)
                center = max(0, source_start - 1)  # 0-based
                w_start = max(0, center - radius)
                w_end = min(len(lines), center + radius)
            else:
                # 行番号がない/信用できない場合は全体をまず試す
                w_start, w_end = 0, len(lines)

            ok, new_lines = self._apply_hunk_within_window(lines, h, w_start, w_end)
            if ok:
                applied += 1
                lines = new_lines
                self.base_logger.debug(
                    f"   [+] Hunk {idx + 1}/{total} applied (window {w_start}:{w_end})."
                )
            else:
                self.base_logger.warning(
                    f"   [=] Hunk {idx + 1}/{total} could not be matched; skipping."
                )

        updated_script = "\n".join(lines)
        if orig_has_trailing_nl and not updated_script.endswith("\n"):
            updated_script += "\n"

        return updated_script, applied, total

    # ---------- Orchestrator ----------

    def _apply_unified_diff(self, original_script: str, diff_text: str) -> str:
        """
        互換API（名前だけ維持）。内部は手書きパーサ＋パターンマッチ適用。
        - 1つでもハンクが適用できればその結果を返す。
        - 全ハンク失敗なら DiffApplyError。
        """
        updated, applied, total = self._apply_diff_by_pattern(
            original_script, diff_text
        )
        if applied == 0:
            raise DiffApplyError("No hunks could be applied.")
        self.base_logger.info(f"   [+] Applied {applied}/{total} hunk(s) successfully.")
        return updated

    def _process_edit_response(self, *, original_script: str, llm_response: str) -> str:
        response_text = llm_response.strip()
        diff_block = self._extract_diff_block(response_text)

        if diff_block:
            sanitized_diff = self._sanitize_patch_text(diff_block)
            try:
                updated = self._apply_unified_diff(original_script, sanitized_diff)
                self.base_logger.debug("   [+] Applied diff-fenced patch successfully.")
                return updated
            except DiffApplyError as exc:
                self.base_logger.error(
                    f"   [-] Failed to apply diff patch: {exc}. Falling back to raw script."
                )

        # diffが使えなかった場合：完成スクリプトが同梱されていれば採用
        cleaned_script = self._strip_code_fence(response_text)
        if "from manim import" in cleaned_script:
            return cleaned_script

        self.base_logger.warning(
            "   [-] No valid diff or script detected. Keeping original script."
        )
        return original_script

    # ============================================================
    # ===============   Generation / Lint / Execute   ============
    # ============================================================

    def generate_script_with_prompt(self, animation_plan: str) -> str:
        """
        生成済みのアニメーションプランから Manim スクリプトを生成する関数
        """
        manim_script_prompt = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"],
        )
        parser = StrOutputParser()

        # プランを instructions として LLM に渡す
        script_chain = manim_script_prompt | self.pro_llm | parser

        script_result = script_chain.invoke({"instructions": animation_plan})

        # LLMが出力するマークダウンを削除
        script_result_cleaned = (
            script_result.strip().replace("```python", "").replace("```", "").strip()
        )

        return script_result_cleaned

    def _generate_initial_script_edit(self, state: ManimGraphState):
        self.base_logger.info(
            "   [+] Edit mode detected. Applying targeted adjustments."
        )
        edit_prompt = PromptTemplate.from_template(
            self.prompts["chain"]["fast_ai_edit_initial"]
        )
        parser = StrOutputParser()
        chain = edit_prompt | self.flash_llm | parser
        llm_response = chain.invoke(
            {
                "edit_instructions": state["user_request"],
                "original_script": state["current_script"],
            }
        )
        self.base_logger.debug(f"llm_response: {llm_response}")

        updated_script = self._process_edit_response(
            original_script=state["current_script"],
            llm_response=llm_response,
        )

        if updated_script != state["current_script"]:
            self.base_logger.debug(
                f"   [+] Applied edit diff (length: {len(updated_script)})"
            )
        else:
            self.base_logger.info(
                "   [=] Edit diff produced no changes. Keeping original script."
            )

        return {
            "current_script": updated_script,
            "current_retry": 0,
            "last_error": "",
            "error_type": "",
        }

    def _generate_initial_script_generate(self, state: ManimGraphState):
        script = self.generate_script_with_prompt(state["animation_plan"])

        self.base_logger.debug(
            f"   [+] Initial script generated (length: {len(script)})"
        )
        return {
            "current_script": script,
            "current_retry": 0,
        }

    def _generate_initial_script(self, state: ManimGraphState):
        """[Node 1] 最初のスクリプトを生成する"""
        self.base_logger.info("--- 1. [Node] Generating Initial Script ---")

        if state["mode"] == "edit":
            return self._generate_initial_script_edit(state)
        else:
            return self._generate_initial_script_generate(state)

    def _run_linter_check(self, state: ManimGraphState):
        self.base_logger.info("--- 2. [Node] Running Manim Linter ---")
        lint_result = self._check_code_lint(state["current_script"])
        status = lint_result.get("status")
        issue_count = lint_result.get("issue_count", len(lint_result.get("issues", [])))

        if status == "pass":
            self.base_logger.debug("   [+] Linter check passed with no warnings.")
            return {"last_error": "", "error_type": ""}

        self.base_logger.warning(
            f"   [-] Linter detected {issue_count} issue(s). Initiating refinement."
        )
        for issue in lint_result.get("issues", []):
            self.base_logger.debug(
                f"      -> {issue.get('filename')}:{issue.get('lineno')} "
                f"[{issue.get('code')}] {issue.get('message')}"
            )
        summary = lint_result.get("summary") or ""
        return {"last_error": summary, "error_type": "lint"}

    def _check_bad_request(self, state: ManimGraphState):
        self.base_logger.info("--- 3. [Node] Checking for Bad Request ---")
        is_safe = self._check_code_security(state["current_script"])
        self.base_logger.debug(
            f"   [+] Code security check: {'Passed' if is_safe else 'Failed'}"
        )
        if not is_safe:
            return {"is_bad_request": True}
        return {"is_bad_request": False}

    def _handle_execution_result(self, execution_result: str, *, stage: str):
        if execution_result == "Success":
            self.base_logger.info(f"   [+] {stage} succeeded.")
            return {
                "last_error": "",
                "error_type": "",
            }
        if execution_result == "bad_request":
            self.base_logger.warning(f"   [-] {stage} detected unsafe code.")
            return {
                "last_error": "The provided script contains unsafe code.",
                "error_type": "runtime",
            }
        if execution_result == "FileNotFoundError":
            self.base_logger.error(
                f"   [-] {stage} failed: Manim executable not found."
            )
            return {
                "last_error": "Manim executable not found.",
                "error_type": "runtime",
            }

        self.base_logger.error(f"   [-] {stage} failed with errors.")
        return {
            "last_error": execution_result,
            "error_type": "runtime",
        }

    def _execute_and_handle_errors(self, state: ManimGraphState):
        """[Node 4] スクリプトを実行し、エラーを処理する
        解像度を落とした事前実行 -> 本実行の2段階での実行
        """

        script = state["current_script"]
        video_id = state["video_id"]
        self.base_logger.info("--- 4. [Node] Preflight Execution Check ---")
        preflight_result = self._handle_execution_result(
            self._execute_script_low_res(script, video_id),
            stage="Preflight execution",
        )
        if preflight_result["error_type"]:
            return preflight_result

        self.base_logger.info("--- 4. [Node] Executing Manim ---")
        runtime_result = self._handle_execution_result(
            self._execute_script(script, video_id),
            stage="Runtime execution",
        )
        return runtime_result

    def _refine_script_on_error(self, state: ManimGraphState):
        """[Node 5] エラーに基づきスクリプトを修正"""
        self.base_logger.info(
            f"--- 5. [Node] Refining Script (Attempt {state['current_retry'] + 1}) ---"
        )

        repair_prompt = PromptTemplate.from_template(
            self.prompts["chain"]["fast_ai_refine_patch"]
        )

        parser = StrOutputParser()

        # エラー処理1回目はflash_llm、それ以降はpro_llmを使用
        if state["current_retry"] == 0:
            self.base_logger.debug("   [+] Using flash_llm for first refinement.")
            chain = repair_prompt | self.flash_llm | parser
        else:
            self.base_logger.debug("   [+] Using pro_llm for subsequent refinements.")
            chain = repair_prompt | self.pro_llm | parser

        fixed_script_response = chain.invoke(
            {
                "lint_summary": state["last_error"],
                "original_script": state["current_script"],
            }
        )
        self.base_logger.debug(f"llm_response: {fixed_script_response}")

        fixed_script = self._process_edit_response(
            original_script=state["current_script"],
            llm_response=fixed_script_response,
        )

        if fixed_script != state["current_script"]:
            self.base_logger.debug(
                f"   [+] Script refined via diff (length: {len(fixed_script)})"
            )
        else:
            self.base_logger.info(
                "   [=] Refinement diff produced no changes. Retaining previous script."
            )

        return {
            "current_script": fixed_script,
            "current_retry": state["current_retry"] + 1,
            "last_error": "",
            "error_type": "",
        }

        # --- 5. グラフの配線 (エッジと条件分岐) ---

    def _after_lint_check(self, state: ManimGraphState):
        """[Conditional Edge] リンターエラーか、リトライ上限か"""
        if state["error_type"] == "lint":
            if state["current_retry"] >= state["max_retries"]:
                self.base_logger.warning(
                    "--- [Branch] Max Retries Reached (Lint Error). Ending. ---"
                )
                return "end_with_error"
            self.base_logger.info(
                "--- [Branch] Linter Failed. Proceeding to Refine. ---"
            )
            return "refine"
        self.base_logger.debug(
            "--- [Branch] Linter Passed. Proceeding to Security Check. ---"
        )
        return "check_bad_request"

    def _after_bad_request_check(self, state: ManimGraphState):
        """[Conditional Edge] 不正リクエストか"""
        if state["is_bad_request"]:
            self.base_logger.error("--- [Branch] Bad Request. Ending Graph. ---")
            return "end_with_error"
        self.base_logger.debug("--- [Branch] Secure. Proceeding to Execute. ---")
        return "execute"

    def _after_execution(self, state: ManimGraphState):
        """[Conditional Edge] 実行時エラーか、リトライ上限か"""
        if state["error_type"] == "runtime":
            if state["current_retry"] >= state["max_retries"]:
                self.base_logger.warning(
                    "--- [Branch] Max Retries Reached (Runtime Error). Ending. ---"
                )
                return "end_with_error"
            self.base_logger.info(
                "--- [Branch] Runtime Error. Proceeding to Refine. ---"
            )
            return "refine"

        self.base_logger.info("--- [Branch] Execution Succeeded. Ending Graph. ---")
        return "end_with_success"

    def _build_graph(self):
        """LangGraphのワークフローを定義・構築する"""
        workflow = StateGraph(ManimGraphState)
        workflow.add_node("generate_initial", self._generate_initial_script)
        workflow.add_node("lint", self._run_linter_check)
        workflow.add_node("check_bad_request", self._check_bad_request)
        workflow.add_node("execute", self._execute_and_handle_errors)
        workflow.add_node("refine", self._refine_script_on_error)
        workflow.set_entry_point("generate_initial")
        workflow.add_edge("generate_initial", "lint")
        workflow.add_edge("refine", "lint")
        workflow.add_conditional_edges(
            "lint",
            self._after_lint_check,
            {
                "refine": "refine",
                "check_bad_request": "check_bad_request",
                "end_with_error": END,
            },
        )
        workflow.add_conditional_edges(
            "check_bad_request",
            self._after_bad_request_check,
            {"execute": "execute", "end_with_error": END},
        )
        workflow.add_conditional_edges(
            "execute",
            self._after_execution,
            {"refine": "refine", "end_with_success": END, "end_with_error": END},
        )
        return workflow

    # ============================================================
    # ==================   Public APIs (same)   ==================
    # ============================================================

    def generate_video(
        self,
        video_id: str,
        content: str,
        enhance_prompt: str,
        maxloop: int = 3,
    ) -> str:
        """
        動画生成のメイン関数
        """
        initial_state: ManimGraphState = {
            "user_request": "",
            "generation_instructions": enhance_prompt,
            "animation_plan": content,
            "video_id": video_id,
            "current_script": "",
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": maxloop,
            "current_retry": 0,
            "mode": "generate",
        }

        final_state = self.app.invoke(initial_state)

        if final_state["is_bad_request"]:
            self.base_logger.error("--- Graph Finished: Bad Request ---")
            return "bad_request"

        if final_state["last_error"]:
            self.base_logger.error(
                f"--- Graph Finished: Error (Max Retries Reached) ---"
            )
            return "error"

        if not final_state["last_error"] and not final_state["is_bad_request"]:
            self.base_logger.info("--- Graph Finished: Success ---")
            return "Success"

        self.base_logger.critical("--- Graph Finished: Fallback (Unknown State) ---")
        return "fall back"

    def edit_video(
        self,
        video_id: str,
        original_script: str,
        edit_instructions: str,
        maxloop: int = 3,
    ) -> str:
        """
        既存のスクリプトを編集して動画を生成するメイン関数
        """
        initial_state: ManimGraphState = {
            "user_request": edit_instructions,
            "generation_instructions": "",
            "animation_plan": "",
            "video_id": video_id,
            "current_script": original_script,
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": maxloop,
            "current_retry": 0,
            "mode": "edit",
        }

        final_state = self.app.invoke(initial_state)

        if final_state["is_bad_request"]:
            self.base_logger.error("--- Graph Finished: Bad Request ---")
            return "bad_request"

        if final_state["last_error"]:
            self.base_logger.error(
                f"--- Graph Finished: Error (Max Retries Reached) ---"
            )
            return "error"

        if not final_state["last_error"] and not final_state["is_bad_request"]:
            self.base_logger.info("--- Graph Finished: Success ---")
            return "Success"

        self.base_logger.critical("--- Graph Finished: Fallback (Unknown State) ---")
        return "fall back"

    def manim_planner(self, content: str, enhance_prompt: str) -> str:
        """
        Manimのアニメーションプランを生成する関数
        """
        manim_planer = PromptTemplate(
            input_variables=["user_prompt"],
            optional_variables=["video_enhance_prompt"],
            template=self.prompts["chain"]["manim_planer_with_instruct"],
        )
        parser = StrOutputParser()

        chain = manim_planer | self.lite_llm | parser

        output: str = chain.invoke(
            {"user_prompt": content, "video_enhance_prompt": enhance_prompt}
        )
        self.base_logger.info(f"Manim planner output: {output}")
        return output
