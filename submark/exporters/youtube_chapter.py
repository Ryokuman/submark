"""YouTube 챕터 writer — Markers에서 chapter 마커만 추출하여 TXT 출력."""

from __future__ import annotations

from pathlib import Path

from submark.models import Markers


def seconds_to_hhmmss(seconds: float) -> str:
    """초 단위 시간을 HH:MM:SS 형식으로 변환한다.

    Args:
        seconds: 초 단위 시간.

    Returns:
        "HH:MM:SS" 형식 문자열.
    """
    total = int(seconds)
    ss = total % 60
    mm = (total // 60) % 60
    hh = total // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def write_chapters(markers: Markers, output_path: Path) -> None:
    """Markers에서 chapter 타입만 필터링하여 YouTube 챕터 TXT로 출력한다.

    Args:
        markers: Markers 객체.
        output_path: 출력 파일 경로.
    """
    chapters = [m for m in markers.markers if m.type == "chapter"]

    lines = []
    for ch in chapters:
        ts = seconds_to_hhmmss(ch.start)
        lines.append(f"{ts} {ch.reason}")

    output_path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")
