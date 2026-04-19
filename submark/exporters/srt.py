"""SRT 자막 writer — Transcript → .srt 파일 생성"""

from __future__ import annotations

from pathlib import Path

from submark.models import Transcript


def format_timestamp(seconds: float) -> str:
    """초(float) → SRT 타임코드 문자열 (HH:MM:SS,mmm)."""
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(transcript: Transcript, output_path: Path) -> Path:
    """Transcript → .srt 파일 생성. 빈 텍스트 세그먼트는 제외."""
    lines: list[str] = []
    seq = 0

    for segment in transcript.segments:
        if not segment.text.strip():
            continue
        seq += 1
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        lines.append(f"{seq}")
        lines.append(f"{start} --> {end}")
        lines.append(segment.text)
        lines.append("")  # 블록 구분 빈 줄

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
