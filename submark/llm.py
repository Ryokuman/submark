"""Gemma/Ollama 래퍼 — Ollama REST API를 통해 로컬 LLM 호출."""

from __future__ import annotations

import json
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3"


def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Ollama API로 프롬프트를 보내고 응답 텍스트를 반환한다.

    Args:
        prompt: LLM에 보낼 프롬프트 문자열.
        model: Ollama 모델 이름 (기본값: gemma3).

    Returns:
        LLM 응답 텍스트 (JSON 문자열이 기대됨).

    Raises:
        ConnectionError: Ollama 서버에 연결할 수 없을 때.
        RuntimeError: API 응답이 비정상일 때.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise ConnectionError(f"Ollama 서버 연결 실패: {e}") from e

    if "response" not in body:
        raise RuntimeError(f"Ollama 응답에 'response' 필드 없음: {body}")

    return body["response"]
