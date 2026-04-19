"""v0.0.2 analyze 테스트 — TDD RED phase

테스트 대상:
- build_prompt: transcript → Gemma 프롬프트 생성
- parse_segment_labels: LLM 응답 (세그먼트별 타입+reason) 파싱
- merge_markers: 인접 동일 타입 세그먼트 → 마커 병합
- analyze: 전체 파이프라인 (LLM mock)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from submark.analyze import analyze, build_prompt, merge_markers, parse_segment_labels
from submark.models import Markers, Transcript

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def transcript() -> Transcript:
    raw = json.loads((FIXTURES / "transcript.json").read_text())
    return Transcript(**raw)


@pytest.fixture
def llm_response_str() -> str:
    """Gemma가 반환할 세그먼트별 분류 결과 (JSON 문자열).

    각 항목은 transcript의 세그먼트 순서와 1:1 대응.
    - type: highlight / cut / chapter / silence / null (마커 없음)
    - reason: 분류 사유 (null이면 생략)
    """
    return json.dumps([
        None,
        {"type": "highlight", "reason": "독일 이주 얘기"},
        {"type": "highlight", "reason": "친구 리액션 강함"},
        {"type": "silence", "reason": "정적 구간"},
        None,
        None,
        {"type": "cut", "reason": "말더듬 반복 (şey 4회)"},
        {"type": "chapter", "reason": "주제 전환: 독일 이주 → 터키 음식"},
    ])


# ── build_prompt ──


class TestBuildPrompt:
    """프롬프트 생성 시 데이터 무결성 + 커스텀 시스템 프롬프트 반영 검증."""

    def test_turkish_special_chars(self, transcript: Transcript):
        """터키어 특수문자(ş, ğ, ç, ı, ö, ü)가 깨지지 않는지."""
        prompt = build_prompt(transcript)
        assert "arkadaşlar" in prompt  # ş
        assert "taşınma" in prompt     # ş
        assert "güzel" in prompt       # ü
        assert "çok" in prompt         # ç
        assert "gidiyorsun" in prompt  # 일반 터키어

    def test_korean_romanization_preserved(self, transcript: Transcript):
        """한국어 음차(annyeonghaseyo)가 유실 없이 전달되는지."""
        prompt = build_prompt(transcript)
        assert "annyeonghaseyo" in prompt

    def test_english_terms_preserved(self, transcript: Transcript):
        """영어 용어(machine learning)가 유실 없이 전달되는지."""
        prompt = build_prompt(transcript)
        assert "machine learning" in prompt

    def test_custom_system_prompt(self, transcript: Transcript):
        """커스텀 시스템 프롬프트가 프롬프트에 반영되는지."""
        custom = "오늘은 웃긴 부분 위주로 찾아줘"
        prompt = build_prompt(transcript, system_prompt=custom)
        assert custom in prompt

    def test_default_without_system_prompt(self, transcript: Transcript):
        """시스템 프롬프트 없이 호출해도 기본 프롬프트가 생성되는지."""
        prompt = build_prompt(transcript)
        assert len(prompt) > 0
        # 기본 지시가 포함되어야 함
        assert "highlight" in prompt


# ── parse_segment_labels ──


class TestParseSegmentLabels:
    """LLM 응답 → 세그먼트별 (type, reason) 리스트 파싱."""

    def test_valid_response(self, llm_response_str: str):
        """정상 JSON → 리스트 반환, 길이 일치."""
        labels = parse_segment_labels(llm_response_str)
        assert len(labels) == 8

    def test_null_entries(self, llm_response_str: str):
        """마커 없는 세그먼트는 None."""
        labels = parse_segment_labels(llm_response_str)
        assert labels[0] is None
        assert labels[4] is None
        assert labels[5] is None

    def test_labeled_entries(self, llm_response_str: str):
        """마커 있는 세그먼트는 type + reason 딕셔너리."""
        labels = parse_segment_labels(llm_response_str)
        assert labels[1]["type"] == "highlight"
        assert labels[1]["reason"] == "독일 이주 얘기"

    def test_invalid_json_raises(self):
        """깨진 문자열 → 에러."""
        with pytest.raises((json.JSONDecodeError, ValueError)):
            parse_segment_labels("이것은 JSON이 아닙니다")


# ── merge_markers ──


class TestMergeMarkers:
    """인접 동일 타입 세그먼트 → 하나의 마커로 병합."""

    def test_adjacent_same_type_merged(self, transcript: Transcript, llm_response_str: str):
        """연속된 highlight(seg_0002 + seg_0003) → 마커 1개."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        highlights = [m for m in markers.markers if m.type == "highlight"]
        assert len(highlights) == 1

    def test_merged_marker_time_range(self, transcript: Transcript, llm_response_str: str):
        """병합된 마커의 start/end는 첫 세그먼트 start ~ 마지막 세그먼트 end."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        highlight = next(m for m in markers.markers if m.type == "highlight")
        # seg_0002.start=4.0, seg_0003.end=10.5
        assert highlight.start == 4.0
        assert highlight.end == 10.5

    def test_merged_marker_source_segments(self, transcript: Transcript, llm_response_str: str):
        """병합된 마커의 source_segments에 원본 세그먼트 id들이 포함."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        highlight = next(m for m in markers.markers if m.type == "highlight")
        assert "seg_0002" in highlight.source_segments
        assert "seg_0003" in highlight.source_segments

    def test_total_marker_count(self, transcript: Transcript, llm_response_str: str):
        """전체 마커 수: highlight 1 + silence 1 + cut 1 + chapter 1 = 4개."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        assert len(markers.markers) == 4

    def test_marker_ids_sequential(self, transcript: Transcript, llm_response_str: str):
        """마커 id가 mk_0001, mk_0002, ... 순번으로 자동 생성."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        ids = [m.id for m in markers.markers]
        assert ids == ["mk_0001", "mk_0002", "mk_0003", "mk_0004"]

    def test_confidence_from_segments(self, transcript: Transcript, llm_response_str: str):
        """마커 confidence는 source 세그먼트들의 평균 confidence."""
        labels = parse_segment_labels(llm_response_str)
        markers = merge_markers(labels, transcript)
        highlight = next(m for m in markers.markers if m.type == "highlight")
        # seg_0002.confidence=0.93, seg_0003.confidence=0.97 → 평균 0.95
        assert highlight.confidence == pytest.approx(0.95)

    def test_all_null_returns_empty(self, transcript: Transcript):
        """전부 None이면 마커 0개."""
        labels = [None] * len(transcript.segments)
        markers = merge_markers(labels, transcript)
        assert len(markers.markers) == 0


# ── analyze pipeline ──


class TestAnalyzePipeline:
    """전체 파이프라인: transcript.json → LLM → markers.json + 내보내기."""

    def test_full_pipeline(self, tmp_path: Path, llm_response_str: str):
        """LLM mock → analyze() → Markers 반환 + markers.json 생성."""
        transcript_path = FIXTURES / "transcript.json"

        with patch("submark.analyze.generate") as mock_gen:
            mock_gen.return_value = llm_response_str
            result = analyze(transcript_path, tmp_path)

        mock_gen.assert_called_once()
        assert isinstance(result, Markers)
        assert len(result.markers) == 4
        assert (tmp_path / "markers.json").exists()

    def test_creates_csv_and_chapters(self, tmp_path: Path, llm_response_str: str):
        """파이프라인이 markers.csv, chapters.txt도 생성."""
        transcript_path = FIXTURES / "transcript.json"

        with patch("submark.analyze.generate") as mock_gen:
            mock_gen.return_value = llm_response_str
            analyze(transcript_path, tmp_path)

        assert (tmp_path / "markers.csv").exists()
        assert (tmp_path / "chapters.txt").exists()
