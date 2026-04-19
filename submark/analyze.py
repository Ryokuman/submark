"""v0.0.2: Gemma 분석 — transcript → markers 파이프라인.

흐름:
1. build_prompt: Transcript → Gemma 프롬프트 생성
2. generate (llm.py): 프롬프트 → LLM 호출 → 세그먼트별 분류 JSON
3. parse_segment_labels: JSON 문자열 → 라벨 리스트
4. merge_markers: 라벨 + Transcript → 인접 동일 타입 병합 → Markers
5. 내보내기: markers.json, markers.csv, chapters.txt
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from submark.llm import generate
from submark.models import Markers, MarkersMetadata, Marker, Transcript
from submark.exporters.premiere_csv import write_csv
from submark.exporters.youtube_chapter import write_chapters

DEFAULT_SYSTEM_PROMPT = """\
You are a podcast editing assistant. Analyze the transcript below and classify \
each segment into one of the following marker types:

- highlight: Interesting, funny, or emotionally engaging moments worth keeping.
- cut: Filler words, stammering, repeated phrases, or NG takes to remove.
- chapter: Topic transition points where the conversation shifts to a new subject.
- silence: Silent or empty segments with no meaningful speech.

If a segment is normal conversation with nothing notable, return null for that segment.

Respond with a JSON array where each element corresponds to a segment in order. \
Each element is either null or an object with "type" and "reason" fields.

Example: [null, {"type": "highlight", "reason": "strong reaction"}, null, ...]
"""


def build_prompt(transcript: Transcript, system_prompt: str | None = None) -> str:
    """Transcript → Gemma에게 보낼 프롬프트를 조립한다.

    Args:
        transcript: Transcript 객체.
        system_prompt: 커스텀 시스템 프롬프트 (None이면 기본값 사용).

    Returns:
        프롬프트 문자열.
    """
    instruction = system_prompt or DEFAULT_SYSTEM_PROMPT

    lines = []
    for seg in transcript.segments:
        lines.append(f"[{seg.start}-{seg.end}] {seg.speaker}: {seg.text}")

    transcript_block = "\n".join(lines)

    return f"{instruction}\n\n## Transcript\n{transcript_block}\n\n## Output\nJSON array:"


def parse_segment_labels(raw_json: str) -> list[dict | None]:
    """LLM 응답 JSON → 세그먼트별 라벨 리스트로 파싱한다.

    Args:
        raw_json: LLM이 반환한 JSON 문자열. 배열 형태.

    Returns:
        각 세그먼트에 대응하는 라벨 리스트. None 또는 {"type": ..., "reason": ...}.

    Raises:
        json.JSONDecodeError: JSON 파싱 실패.
        ValueError: 파싱 결과가 리스트가 아닐 때.
    """
    parsed = json.loads(raw_json)
    if not isinstance(parsed, list):
        raise ValueError(f"JSON 배열이 아님: {type(parsed)}")
    return parsed


def merge_markers(labels: list[dict | None], transcript: Transcript) -> Markers:
    """세그먼트별 라벨을 인접 동일 타입 기준으로 병합하여 Markers를 생성한다.

    Args:
        labels: parse_segment_labels()의 반환값.
        transcript: 원본 Transcript 객체 (시간, confidence 등 참조).

    Returns:
        병합된 Markers 객체.
    """
    segments = transcript.segments
    markers: list[Marker] = []
    group: list[int] = []  # 현재 그룹의 세그먼트 인덱스들
    current_type: str | None = None

    def flush_group() -> None:
        """현재 그룹을 마커로 변환하고 markers에 추가."""
        if not group:
            return
        marker_id = f"mk_{len(markers) + 1:04d}"
        group_segments = [segments[i] for i in group]
        group_labels = [labels[i] for i in group]

        reasons = [lb["reason"] for lb in group_labels if lb and lb.get("reason")]
        reason = "; ".join(reasons) if reasons else ""

        avg_confidence = (
            sum(s.confidence for s in group_segments) / len(group_segments)
        )

        markers.append(Marker(
            id=marker_id,
            start=group_segments[0].start,
            end=group_segments[-1].end,
            type=current_type,
            reason=reason,
            confidence=round(avg_confidence, 4),
            source_segments=[s.id for s in group_segments],
        ))

    for i, label in enumerate(labels):
        label_type = label["type"] if label else None

        if label_type is None:
            flush_group()
            group = []
            current_type = None
        elif label_type == current_type:
            group.append(i)
        else:
            flush_group()
            group = [i]
            current_type = label_type

    flush_group()

    return Markers(
        metadata=MarkersMetadata(
            transcript_id=transcript.metadata.source,
            generated_by="gemma3",
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        markers=markers,
    )


def analyze(
    transcript_path: Path,
    output_dir: Path,
    model: str = "gemma3",
    system_prompt: str | None = None,
) -> Markers:
    """전체 분석 파이프라인: transcript.json → markers + 내보내기.

    Args:
        transcript_path: transcript.json 파일 경로.
        output_dir: 출력 디렉토리.
        model: Ollama 모델 이름.
        system_prompt: 커스텀 시스템 프롬프트.

    Returns:
        생성된 Markers 객체.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript = Transcript(**raw)

    prompt = build_prompt(transcript, system_prompt=system_prompt)
    raw_response = generate(prompt, model=model)

    labels = parse_segment_labels(raw_response)
    markers = merge_markers(labels, transcript)

    (output_dir / "markers.json").write_text(
        markers.model_dump_json(indent=2), encoding="utf-8"
    )

    write_csv(markers, output_dir / "markers.csv")
    write_chapters(markers, output_dir / "chapters.txt")

    return markers
