"""v0.0.2 (feat/analyze) 테스트 — 구현 시 채울 것

테스트 목표 (mock transcript.json 사용):
- Gemma 프롬프트가 올바른 형태로 생성되는지
- LLM 응답 → Markers 스키마 파싱
- 마커 4종(highlight/cut/chapter/silence) 분류 정상
- Premiere CSV 포맷 정상 출력
- YouTube 챕터 TXT 포맷 정상 출력
"""

import pytest


@pytest.mark.skip(reason="feat/analyze 브랜치에서 구현")
def test_prompt_generation():
    """transcript → Gemma 프롬프트 생성"""


@pytest.mark.skip(reason="feat/analyze 브랜치에서 구현")
def test_marker_classification():
    """LLM 응답 → highlight/cut/chapter/silence 분류"""


@pytest.mark.skip(reason="feat/analyze 브랜치에서 구현")
def test_premiere_csv_export():
    """Markers → Premiere CSV 포맷"""


@pytest.mark.skip(reason="feat/analyze 브랜치에서 구현")
def test_youtube_chapter_export():
    """Markers → YouTube 챕터 TXT"""
