from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib import error as url_error
from urllib import request as url_request

from dotenv import load_dotenv, find_dotenv


class GeminiClientError(RuntimeError):
    """Raised when Gemini text generation cannot be initialised."""


class GeminiTextClient:
    """Minimal helper for invoking the Gemini REST API."""

    _DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, *, base_url: str | None = None, timeout: float = 300.0) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._base_url = (base_url or self._DEFAULT_BASE_URL).rstrip("/")

    def generate(self, model_name: str, prompt: str) -> str:
        try:
            response = self._call_generate(model_name, prompt)
        except url_error.HTTPError as exc:
            text = self._read_error_body(exc)
            message = f"Gemini API request failed ({exc.code})"
            if text:
                message = f"{message}: {text}"
            raise GeminiClientError(message) from exc
        except url_error.URLError as exc:
            raise GeminiClientError(f"Gemini API request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise GeminiClientError("Gemini API returned invalid JSON payload.") from exc

        text = self._extract_text(response.get("candidates", []))
        return text or ""

    def _call_generate(self, model_name: str, prompt: str) -> Dict[str, Any]:
        url = f"{self._base_url}/models/{model_name}:generateContent"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = url_request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
        )
        with url_request.urlopen(req, timeout=self._timeout) as resp:
            body = resp.read()
            if not body:
                return {}
            return json.loads(body.decode("utf-8"))

    @staticmethod
    def _extract_text(candidates: Iterable[Dict[str, Any]]) -> str:
        for candidate in candidates or []:
            content = candidate.get("content") or {}
            for part in content.get("parts", []) or []:
                text = part.get("text")
                if text:
                    return text
        return ""

    @staticmethod
    def _read_error_body(exc: url_error.HTTPError) -> str:
        try:
            data = exc.read()
        except Exception:  # pragma: no cover - best effort
            return ""
        if not data:
            return ""
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception:
            return data.decode("utf-8", errors="ignore")
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        return json.dumps(payload)


def load_api_key(env_path: str | None = None) -> str:
    """Load GEMINI_API_KEY from .env. Raises GeminiClientError if missing."""
    if env_path:
        env_file = Path(env_path)
        if not env_file.exists():
            raise GeminiClientError(f"Specified .env file not found: {env_path}")
        load_dotenv(env_file)
    else:
        load_dotenv(find_dotenv(usecwd=True))

    from os import getenv

    api_key = getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiClientError("Environment variable GEMINI_API_KEY is required. Set it in your .env file.")
    return api_key
