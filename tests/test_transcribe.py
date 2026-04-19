"""v0.0.1 (feat/transcribe) 테스트 — 구현 시 채울 것

테스트 목표:
- ffmpeg로 영상 → wav 추출 정상 동작
- WhisperX 래퍼가 transcript.json 생성
- 출력이 Transcript 스키마에 맞는지 검증
- SRT 파일 정상 생성
- 화자분리(speaker) 필드가 채워지는지 확인
"""

import pytest


@pytest.mark.skip(reason="feat/transcribe 브랜치에서 구현")
def test_audio_extraction():
    """영상 파일 → wav 추출"""


@pytest.mark.skip(reason="feat/transcribe 브랜치에서 구현")
def test_whisperx_output_schema():
    """WhisperX 출력 → Transcript 스키마 변환"""


@pytest.mark.skip(reason="feat/transcribe 브랜치에서 구현")
def test_srt_export():
    """Transcript → SRT 파일 생성"""


@pytest.mark.skip(reason="feat/transcribe 브랜치에서 구현")
def test_speaker_diarization():
    """화자분리 필드가 존재하고 비어있지 않은지"""
