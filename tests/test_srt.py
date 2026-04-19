"""SRT Writer 테스트

검증 대상: submark/exporters/srt.py
- format_timestamp(): 초(float) → SRT 타임코드 문자열 변환
- write_srt(): Transcript → .srt 파일 생성

SRT 포맷 규칙:
  1
  00:00:00,000 --> 00:00:03,500
  자막 텍스트

  2
  00:00:04,000 --> 00:00:07,200
  다음 자막 텍스트
"""

import json
from pathlib import Path

import pytest

from submark.exporters.srt import format_timestamp, write_srt
from submark.models import Transcript

FIXTURES = Path(__file__).parent / "fixtures"


# ── format_timestamp ──


class TestFormatTimestamp:
    """초(float) → SRT 타임코드 변환 테스트.

    SRT 타임코드 형식: HH:MM:SS,mmm
    - 시:분:초는 콜론(:)으로 구분
    - 초와 밀리초는 콤마(,)로 구분 (. 이 아님!)
    """

    def test_basic_conversion(self):
        """83.456초 → 00:01:23,456"""
        assert format_timestamp(83.456) == "00:01:23,456"

    def test_zero(self):
        """0초 → 00:00:00,000"""
        assert format_timestamp(0.0) == "00:00:00,000"

    def test_one_hour_plus(self):
        """3661.5초 (1시간 1분 1.5초) → 01:01:01,500"""
        assert format_timestamp(3661.5) == "01:01:01,500"

    def test_sub_second(self):
        """0.123초 — 밀리초만 있는 경우"""
        assert format_timestamp(0.123) == "00:00:00,123"

    def test_whole_seconds(self):
        """정수 초 — 밀리초가 000이어야 함"""
        assert format_timestamp(10.0) == "00:00:10,000"

    def test_rounding_precision(self):
        """부동소수점 오차로 밀리초가 깨지지 않는지 확인.

        예: 1.9999999 → 00:00:02,000 이 아니라 00:00:01,999 (truncate 혹은 round)
        구현에 따라 달라질 수 있으나, 최소한 유효한 타임코드여야 함.
        """
        result = format_timestamp(1.9999)
        # 형식이 올바른지만 확인 (HH:MM:SS,mmm)
        parts = result.split(",")
        assert len(parts) == 2
        assert len(parts[1]) == 3  # 밀리초는 항상 3자리


# ── write_srt ──


class TestWriteSrt:
    """Transcript → SRT 파일 생성 테스트.

    fixture의 transcript.json을 입력으로 사용.
    """

    @pytest.fixture
    def transcript(self) -> Transcript:
        """테스트용 Transcript 객체 (fixture에서 로드)."""
        raw = json.loads((FIXTURES / "transcript.json").read_text())
        return Transcript(**raw)

    def test_file_created(self, transcript: Transcript, tmp_path: Path):
        """SRT 파일이 지정된 경로에 생성되는지."""
        output = tmp_path / "subtitle.srt"
        result = write_srt(transcript, output)

        assert result == output
        assert output.exists()

    def test_utf8_encoding(self, transcript: Transcript, tmp_path: Path):
        """터키어 특수문자(ş, ğ, ç 등)가 깨지지 않도록 UTF-8 인코딩."""
        output = tmp_path / "subtitle.srt"
        write_srt(transcript, output)

        content = output.read_text(encoding="utf-8")
        # 터키어 특수문자가 포함된 세그먼트가 있는지 확인
        assert "arkadaşlar" in content
        assert "güzel" in content

    def test_srt_sequence_numbers(self, transcript: Transcript, tmp_path: Path):
        """SRT 시퀀스 번호가 1부터 순차적으로 부여되는지.

        빈 세그먼트(text="")는 건너뛰므로 번호가 연속이어야 함.
        fixture에 8개 세그먼트 중 1개가 빈 텍스트 → 7개 자막.
        """
        output = tmp_path / "subtitle.srt"
        write_srt(transcript, output)

        content = output.read_text(encoding="utf-8")
        blocks = [b.strip() for b in content.strip().split("\n\n")]
        # 빈 세그먼트(seg_0004) 제외 → 7개
        assert len(blocks) == 7
        # 시퀀스 번호 확인
        for i, block in enumerate(blocks, start=1):
            first_line = block.split("\n")[0]
            assert first_line == str(i)

    def test_empty_segments_skipped(self, transcript: Transcript, tmp_path: Path):
        """text가 빈 문자열인 세그먼트는 SRT에 포함되지 않아야 함.

        fixture의 seg_0004는 text="" → 자막에서 제외.
        """
        output = tmp_path / "subtitle.srt"
        write_srt(transcript, output)

        content = output.read_text(encoding="utf-8")
        # 빈 세그먼트의 타임코드(12.0~12.3)가 없어야 함
        assert "00:00:12,000" not in content

    def test_timestamp_arrows(self, transcript: Transcript, tmp_path: Path):
        """타임코드가 'HH:MM:SS,mmm --> HH:MM:SS,mmm' 형식인지.

        첫 번째 세그먼트: 0.0 ~ 3.5초
        """
        output = tmp_path / "subtitle.srt"
        write_srt(transcript, output)

        content = output.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:03,500" in content

    def test_subtitle_text_content(self, transcript: Transcript, tmp_path: Path):
        """자막 텍스트가 원본 그대로 들어가는지.

        SRT writer는 텍스트를 변환하지 않음 (음차 복원은 v0.0.3 render 단계).
        """
        output = tmp_path / "subtitle.srt"
        write_srt(transcript, output)

        content = output.read_text(encoding="utf-8")
        assert "Merhaba arkadaşlar, bugün çok güzel bir konumuz var." in content
        assert "Evet, Almanya'ya taşınma hikayemi anlatacağım." in content
