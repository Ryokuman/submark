"""모델 스키마 검증 테스트 — 셋업 단계에서 mock data가 스키마에 맞는지 확인"""

import json
from pathlib import Path

from submark.models import Markers, Transcript

FIXTURES = Path(__file__).parent / "fixtures"


def test_transcript_schema():
    """transcript.json mock이 Transcript 스키마에 맞는지 확인"""
    raw = json.loads((FIXTURES / "transcript.json").read_text())
    t = Transcript(**raw)

    assert t.metadata.language == "tr"
    assert len(t.metadata.speakers) == 2
    assert len(t.segments) == 8
    # 단어 타임스탬프 존재
    assert len(t.segments[0].words) > 0
    assert t.segments[0].words[0].start >= 0.0


def test_markers_schema():
    """markers.json mock이 Markers 스키마에 맞는지 확인"""
    raw = json.loads((FIXTURES / "markers.json").read_text())
    m = Markers(**raw)

    assert len(m.markers) == 4
    types = {mk.type for mk in m.markers}
    assert types == {"highlight", "silence", "cut", "chapter"}
