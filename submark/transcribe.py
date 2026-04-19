"""v0.0.1: WhisperX 래퍼 — 영상 → Transcript 파이프라인"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import ffmpeg

from submark.exporters.srt import write_srt
from submark.models import Segment, Transcript, TranscriptMetadata, Word


def extract_audio(input_path: Path, output_path: Path) -> Path:
    """영상 파일 → WAV (16kHz, mono) 오디오 추출."""
    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")

    (
        ffmpeg
        .input(str(input_path))
        .output(str(output_path), ar=16000, ac=1, format="wav")
        .overwrite_output()
        .run()
    )
    return output_path


def run_whisperx(
    audio_path: Path,
    language: str = os.getenv("SUBMARK_LANGUAGE", "tr"),
    model_size: str = os.getenv("SUBMARK_MODEL_SIZE", "large-v3"),
    diarize: bool = os.getenv("SUBMARK_DIARIZE", "true").lower() == "true",
    min_speakers: int | None = int(v) if (v := os.getenv("SUBMARK_MIN_SPEAKERS")) else None,
    max_speakers: int | None = int(v) if (v := os.getenv("SUBMARK_MAX_SPEAKERS")) else None,
    compute_type: str = os.getenv("SUBMARK_COMPUTE_TYPE", "auto"),
) -> dict:
    """WhisperX 실행 → raw dict 반환.

    실제 WhisperX 호출은 whisperx 패키지가 설치된 환경에서만 동작.
    """
    import whisperx

    device = "cpu"
    model = whisperx.load_model(
        model_size, device, compute_type=compute_type, language=language,
    )
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio)

    # 단어 단위 정렬
    align_model, align_metadata = whisperx.load_align_model(
        language_code=language, device=device,
    )
    result = whisperx.align(
        result["segments"], align_model, align_metadata, audio, device,
    )

    # 화자 분리
    if diarize:
        diarize_model = whisperx.DiarizationPipeline(device=device)
        diarize_kwargs = {}
        if min_speakers is not None:
            diarize_kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            diarize_kwargs["max_speakers"] = max_speakers
        diarize_segments = diarize_model(audio, **diarize_kwargs)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    return result


def parse_whisperx_output(
    raw: dict,
    source: str,
    min_confidence: float = float(os.getenv("SUBMARK_MIN_CONFIDENCE", "0.0")),
    merge_threshold: float = float(os.getenv("SUBMARK_MERGE_THRESHOLD", "0.0")),
) -> Transcript:
    """WhisperX raw dict → Transcript 스키마 변환."""
    segments: list[Segment] = []
    all_speakers: set[str] = set()
    max_end = 0.0

    for i, seg in enumerate(raw["segments"], start=1):
        speaker = seg.get("speaker", "UNKNOWN")
        all_speakers.add(speaker)

        words = [
            Word(word=w["word"], start=w["start"], end=w["end"], score=w.get("score", 0.0))
            for w in seg.get("words", [])
        ]

        if words:
            confidence = sum(w.score for w in words) / len(words)
        else:
            confidence = 0.0

        seg_end = seg["end"]
        if seg_end > max_end:
            max_end = seg_end

        segments.append(
            Segment(
                id=f"seg_{i:04d}",
                start=seg["start"],
                end=seg_end,
                text=seg.get("text", ""),
                speaker=speaker,
                words=words,
                confidence=confidence,
            )
        )

    metadata = TranscriptMetadata(
        source=source,
        duration=max_end,
        language=raw.get("language", "tr"),
        speakers=sorted(all_speakers),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return Transcript(metadata=metadata, segments=segments)


def transcribe_pipeline(
    input_path: Path,
    output_dir: Path,
    language: str = os.getenv("SUBMARK_LANGUAGE", "tr"),
) -> Transcript:
    """전체 파이프라인: extract → whisperx → parse → JSON + SRT 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 오디오 추출
    wav_path = output_dir / "audio.wav"
    extract_audio(input_path, wav_path)

    # 2. WhisperX 실행
    raw = run_whisperx(wav_path, language=language)

    # 3. 파싱
    transcript = parse_whisperx_output(raw, source=input_path.name)

    # 4. JSON 저장
    transcript_path = output_dir / "transcript.json"
    transcript_path.write_text(
        transcript.model_dump_json(indent=2), encoding="utf-8",
    )

    # 5. SRT 저장
    srt_path = output_dir / "subtitle.srt"
    write_srt(transcript, srt_path)

    return transcript
