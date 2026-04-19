"""Premiere CSV 마커 writer — Markers → Premiere import용 CSV."""

from __future__ import annotations

from pathlib import Path

from submark.models import Markers

HEADER = "Marker Name,Description,In,Out,Duration,Marker Type"
FPS = 30


def seconds_to_timecode(seconds: float, fps: int = FPS) -> str:
    """초 단위 시간을 Premiere 타임코드(HH:MM:SS:FF)로 변환한다.

    Args:
        seconds: 초 단위 시간.
        fps: 프레임 레이트 (기본값: 30).

    Returns:
        "HH:MM:SS:FF" 형식 문자열.
    """
    total_frames = int(seconds * fps)
    ff = total_frames % fps
    total_seconds = total_frames // fps
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def write_csv(markers: Markers, output_path: Path) -> None:
    """Markers → Premiere CSV 파일로 출력한다.

    Args:
        markers: Markers 객체.
        output_path: 출력 파일 경로.
    """
    lines = [HEADER]

    for marker in markers.markers:
        name = f"{marker.type}: {marker.reason}"
        description = marker.reason
        tc_in = seconds_to_timecode(marker.start)
        tc_out = seconds_to_timecode(marker.end)

        duration_secs = marker.end - marker.start
        tc_duration = seconds_to_timecode(duration_secs)

        lines.append(
            f'"{name}","{description}",{tc_in},{tc_out},{tc_duration},Comment'
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
