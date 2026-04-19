"""Transcribe 파이프라인 테스트

검증 대상: submark/transcribe.py
- extract_audio(): 영상 → wav 오디오 추출 (ffmpeg 래핑)
- parse_whisperx_output(): WhisperX raw dict → Transcript 스키마 변환
- transcribe_pipeline(): 전체 파이프라인 통합 (extract → whisperx → parse → export)

외부 의존성(ffmpeg, whisperx)은 mock으로 처리하여
실제 바이너리 없이도 로직을 검증할 수 있게 함.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from submark.models import Transcript
from submark.transcribe import extract_audio, parse_whisperx_output, transcribe_pipeline

FIXTURES = Path(__file__).parent / "fixtures"


# ── extract_audio ──


class TestExtractAudio:
    """ffmpeg를 통한 오디오 추출 테스트.

    영상(MP4/MOV 등) → WAV (16kHz, mono) 변환.
    ffmpeg-python 라이브러리의 호출을 mock하여 검증.
    """

    @patch("submark.transcribe.ffmpeg")
    def test_calls_ffmpeg_with_correct_params(self, mock_ffmpeg: MagicMock, tmp_path: Path):
        """ffmpeg가 16kHz mono WAV로 변환하도록 호출되는지.

        핵심 인자:
        - ar=16000 (샘플레이트 16kHz — Whisper 권장)
        - ac=1 (모노 채널)
        - format='wav'
        """
        input_file = tmp_path / "test.mp4"
        input_file.touch()  # 빈 파일 생성 (존재 확인용)
        output_file = tmp_path / "audio.wav"

        # ffmpeg 체이닝 mock 설정: ffmpeg.input().output().overwrite_output().run()
        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream

        extract_audio(input_file, output_file)

        # ffmpeg.input이 입력 파일로 호출되었는지
        mock_ffmpeg.input.assert_called_once_with(str(input_file))
        # output에 올바른 오디오 파라미터가 전달되었는지
        mock_stream.output.assert_called_once_with(
            str(output_file), ar=16000, ac=1, format="wav"
        )
        # 실제 실행(run)이 호출되었는지
        mock_stream.overwrite_output.assert_called_once()
        mock_stream.run.assert_called_once()

    def test_raises_on_missing_file(self, tmp_path: Path):
        """존재하지 않는 입력 파일 → FileNotFoundError.

        ffmpeg 호출 전에 파일 존재를 확인하여 빠르게 실패해야 함.
        """
        fake_input = tmp_path / "nonexistent.mp4"
        output_file = tmp_path / "audio.wav"

        with pytest.raises(FileNotFoundError):
            extract_audio(fake_input, output_file)


# ── parse_whisperx_output ──


class TestParseWhisperxOutput:
    """WhisperX raw dict → Transcript 변환 테스트.

    WhisperX는 자체 dict 구조로 결과를 반환함.
    이를 우리의 Pydantic Transcript 스키마로 변환하는 로직을 검증.

    fixture: tests/fixtures/whisperx_raw.json
    """

    @pytest.fixture
    def raw_output(self) -> dict:
        """WhisperX가 반환하는 형태의 mock raw dict."""
        return json.loads((FIXTURES / "whisperx_raw.json").read_text())

    def test_returns_transcript_model(self, raw_output: dict):
        """반환 타입이 Transcript (Pydantic 모델)인지."""
        result = parse_whisperx_output(raw_output, source="test.mp4")
        assert isinstance(result, Transcript)

    def test_metadata_fields(self, raw_output: dict):
        """metadata에 source, language, speakers, created_at이 올바르게 설정되는지."""
        result = parse_whisperx_output(raw_output, source="podcast_ep01.mp4")

        assert result.metadata.source == "podcast_ep01.mp4"
        assert result.metadata.language == "tr"
        # WhisperX raw에 SPEAKER_00, SPEAKER_01 두 화자가 있음
        assert set(result.metadata.speakers) == {"SPEAKER_00", "SPEAKER_01"}
        # created_at은 ISO 8601 형식이어야 함
        assert "T" in result.metadata.created_at

    def test_segment_ids_generated(self, raw_output: dict):
        """각 세그먼트에 고유 ID(seg_XXXX)가 부여되는지.

        WhisperX raw에는 ID가 없으므로 parse 단계에서 생성해야 함.
        """
        result = parse_whisperx_output(raw_output, source="test.mp4")

        ids = [seg.id for seg in result.segments]
        # 중복 없음
        assert len(ids) == len(set(ids))
        # seg_ 접두사
        for seg_id in ids:
            assert seg_id.startswith("seg_")

    def test_segment_count_matches(self, raw_output: dict):
        """WhisperX raw의 세그먼트 수와 변환 후 세그먼트 수가 일치하는지.

        빈 세그먼트도 포함 (필터링은 SRT writer의 책임).
        """
        result = parse_whisperx_output(raw_output, source="test.mp4")
        assert len(result.segments) == len(raw_output["segments"])

    def test_word_timestamps_preserved(self, raw_output: dict):
        """단어 단위 타임스탬프와 score가 보존되는지.

        WhisperX word의 word/start/end/score 모두 우리 Word 모델로 매핑.
        score는 단어별 confidence로, 나중에 어떤 단어가 불확실한지 추적할 때 필요.
        """
        result = parse_whisperx_output(raw_output, source="test.mp4")

        first_seg = result.segments[0]
        assert len(first_seg.words) == 8
        assert first_seg.words[0].word == "Merhaba"
        assert first_seg.words[0].start == 0.0
        assert first_seg.words[0].end == 0.5
        assert first_seg.words[0].score == 0.95

    def test_speaker_field_mapped(self, raw_output: dict):
        """WhisperX의 speaker 필드가 그대로 매핑되는지."""
        result = parse_whisperx_output(raw_output, source="test.mp4")

        assert result.segments[0].speaker == "SPEAKER_00"
        assert result.segments[1].speaker == "SPEAKER_01"

    def test_confidence_from_word_scores(self, raw_output: dict):
        """세그먼트 confidence가 해당 세그먼트 단어들의 score 평균으로 계산되는지.

        WhisperX는 세그먼트 레벨 confidence를 주지 않으므로,
        단어별 score의 평균을 사용함.
        빈 세그먼트(words=[])는 confidence=0.0.
        """
        result = parse_whisperx_output(raw_output, source="test.mp4")

        # 첫 번째 세그먼트: 8개 단어의 score 평균
        first_seg = result.segments[0]
        expected_scores = [0.95, 0.93, 0.97, 0.96, 0.94, 0.98, 0.91, 0.95]
        expected_avg = sum(expected_scores) / len(expected_scores)
        assert abs(first_seg.confidence - expected_avg) < 0.001

        # 빈 세그먼트: confidence=0.0
        empty_seg = result.segments[2]
        assert empty_seg.confidence == 0.0

    def test_duration_calculated(self, raw_output: dict):
        """metadata.duration이 마지막 세그먼트의 end 값으로 설정되는지.

        실제 영상 길이는 ffprobe로 알 수 있지만,
        parse 단계에서는 세그먼트 기준으로 대략적인 duration을 설정.
        """
        result = parse_whisperx_output(raw_output, source="test.mp4")
        # raw fixture의 마지막 세그먼트 end: 12.3
        assert result.metadata.duration == 12.3


# ── transcribe_pipeline ──


class TestTranscribePipeline:
    """전체 파이프라인 통합 테스트.

    extract_audio → run_whisperx → parse → JSON 저장 + SRT 생성.
    모든 외부 의존성을 mock하여 파이프라인 흐름만 검증.
    """

    @patch("submark.transcribe.write_srt")
    @patch("submark.transcribe.run_whisperx")
    @patch("submark.transcribe.extract_audio")
    def test_pipeline_creates_output_files(
        self,
        mock_extract: MagicMock,
        mock_whisperx: MagicMock,
        mock_write_srt: MagicMock,
        tmp_path: Path,
    ):
        """파이프라인 실행 후 transcript.json과 subtitle.srt가 생성되는지.

        mock 체인:
        1. extract_audio → wav 경로 반환
        2. run_whisperx → fixture의 raw dict 반환
        3. write_srt → srt 경로 반환
        """
        input_file = tmp_path / "test.mp4"
        input_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # mock 설정
        wav_path = tmp_path / "audio.wav"
        mock_extract.return_value = wav_path

        raw = json.loads((FIXTURES / "whisperx_raw.json").read_text())
        mock_whisperx.return_value = raw

        srt_path = output_dir / "subtitle.srt"
        mock_write_srt.return_value = srt_path

        # 파이프라인 실행
        result = transcribe_pipeline(input_file, output_dir, language="tr")

        # extract_audio가 호출되었는지
        mock_extract.assert_called_once()
        # run_whisperx가 올바른 언어로 호출되었는지
        mock_whisperx.assert_called_once()
        call_kwargs = mock_whisperx.call_args
        assert call_kwargs[1].get("language", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None) == "tr" or "tr" in str(call_kwargs)

        # transcript.json이 생성되었는지
        transcript_json = output_dir / "transcript.json"
        assert transcript_json.exists()

        # JSON이 Transcript 스키마에 맞는지
        saved = json.loads(transcript_json.read_text())
        transcript = Transcript(**saved)
        assert transcript.metadata.language == "tr"

        # write_srt가 호출되었는지
        mock_write_srt.assert_called_once()

    @patch("submark.transcribe.write_srt")
    @patch("submark.transcribe.run_whisperx")
    @patch("submark.transcribe.extract_audio")
    def test_pipeline_creates_output_dir_if_not_exists(
        self,
        mock_extract: MagicMock,
        mock_whisperx: MagicMock,
        mock_write_srt: MagicMock,
        tmp_path: Path,
    ):
        """출력 디렉토리가 없으면 자동 생성해야 함."""
        input_file = tmp_path / "test.mp4"
        input_file.touch()
        output_dir = tmp_path / "new_output"  # 아직 존재하지 않음

        mock_extract.return_value = tmp_path / "audio.wav"
        raw = json.loads((FIXTURES / "whisperx_raw.json").read_text())
        mock_whisperx.return_value = raw
        mock_write_srt.return_value = output_dir / "subtitle.srt"

        transcribe_pipeline(input_file, output_dir, language="tr")

        assert output_dir.exists()
