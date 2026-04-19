"""Pydantic 데이터 모델 — Transcript & Markers"""

from __future__ import annotations

from pydantic import BaseModel


# ── Transcript (v0.0.1) ──


class Word(BaseModel):
    word: str
    start: float
    end: float
    score: float


class Segment(BaseModel):
    id: str
    start: float
    end: float
    text: str
    speaker: str
    words: list[Word]
    confidence: float


class TranscriptMetadata(BaseModel):
    source: str
    duration: float
    language: str = "tr"
    speakers: list[str]
    created_at: str


class Transcript(BaseModel):
    metadata: TranscriptMetadata
    segments: list[Segment]


# ── Markers (v0.0.2) ──


class MarkerType:
    HIGHLIGHT = "highlight"
    CUT = "cut"
    CHAPTER = "chapter"
    SILENCE = "silence"


class Marker(BaseModel):
    id: str
    start: float
    end: float
    type: str  # MarkerType values
    reason: str
    confidence: float
    source_segments: list[str]


class MarkersMetadata(BaseModel):
    transcript_id: str
    generated_by: str
    created_at: str


class Markers(BaseModel):
    metadata: MarkersMetadata
    markers: list[Marker]
