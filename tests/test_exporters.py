"""v0.0.2 exporters 테스트 — TDD RED phase

테스트 대상:
- premiere_csv: Markers → Premiere CSV 포맷
- youtube_chapter: Markers → YouTube 챕터 TXT
"""

import json
from pathlib import Path

import pytest

from submark.exporters.premiere_csv import seconds_to_timecode, write_csv
from submark.exporters.youtube_chapter import write_chapters
from submark.models import Markers

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def markers() -> Markers:
    raw = json.loads((FIXTURES / "markers.json").read_text())
    return Markers(**raw)


# ── Premiere CSV ──


class TestPremiereCSV:
    def test_timecode_zero(self):
        assert seconds_to_timecode(0.0) == "00:00:00:00"

    def test_timecode_simple(self):
        # 65.5초 = 1분 5초 15프레임 (30fps 기준: 0.5 * 30 = 15)
        assert seconds_to_timecode(65.5) == "00:01:05:15"

    def test_timecode_hours(self):
        # 3661.0초 = 1시간 1분 1초
        assert seconds_to_timecode(3661.0) == "01:01:01:00"

    def test_csv_header(self, markers: Markers, tmp_path: Path):
        out = tmp_path / "markers.csv"
        write_csv(markers, out)
        lines = out.read_text().strip().split("\n")
        assert lines[0] == "Marker Name,Description,In,Out,Duration,Marker Type"

    def test_csv_row_count(self, markers: Markers, tmp_path: Path):
        out = tmp_path / "markers.csv"
        write_csv(markers, out)
        lines = out.read_text().strip().split("\n")
        # 헤더 1줄 + 마커 4개
        assert len(lines) == 5

    def test_csv_highlight_row(self, markers: Markers, tmp_path: Path):
        out = tmp_path / "markers.csv"
        write_csv(markers, out)
        content = out.read_text()
        # highlight 마커가 포함되어야 함
        assert "highlight" in content.lower() or "하이라이트" in content

    def test_csv_marker_type_column(self, markers: Markers, tmp_path: Path):
        """모든 행의 Marker Type 열이 'Comment'이어야 함 (Premiere 규격)."""
        out = tmp_path / "markers.csv"
        write_csv(markers, out)
        lines = out.read_text().strip().split("\n")
        for line in lines[1:]:  # 헤더 제외
            assert line.strip().endswith("Comment")


# ── YouTube 챕터 ──


class TestYouTubeChapters:
    def test_only_chapter_markers(self, markers: Markers, tmp_path: Path):
        out = tmp_path / "chapters.txt"
        write_chapters(markers, out)
        lines = out.read_text().strip().split("\n")
        # markers.json에 chapter 마커는 1개
        assert len(lines) == 1

    def test_format(self, markers: Markers, tmp_path: Path):
        out = tmp_path / "chapters.txt"
        write_chapters(markers, out)
        line = out.read_text().strip()
        # "00:00:30 주제 전환: 독일 이주 → 터키 음식" 형태
        assert line.startswith("00:00:30")
        assert "주제 전환" in line

    def test_empty_when_no_chapters(self, tmp_path: Path):
        """chapter 타입 마커가 없으면 빈 파일."""
        no_chapters = Markers(
            metadata={
                "transcript_id": "test",
                "generated_by": "test",
                "created_at": "2026-04-19T00:00:00Z",
            },
            markers=[],
        )
        out = tmp_path / "chapters.txt"
        write_chapters(no_chapters, out)
        assert out.read_text().strip() == ""
