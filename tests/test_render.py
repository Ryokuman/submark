"""v0.0.3 (feat/render) 테스트 — 구현 시 채울 것

테스트 목표 (mock transcript.json + markers.json 사용):
- cut 마커 구간이 자막에서 제거되는지
- 한/영 음차가 원래 언어로 복원되는지 (annyeonghaseyo → 안녕하세요)
- 줄당 글자수 제한 적용
- 최종 SRT 타임코드 정확성
"""

import pytest


@pytest.mark.skip(reason="feat/render 브랜치에서 구현")
def test_cut_segments_removed():
    """cut 마커 구간(seg_0007)이 final.srt에서 제외"""


@pytest.mark.skip(reason="feat/render 브랜치에서 구현")
def test_transliteration_restore():
    """음차 복원: annyeonghaseyo → 안녕하세요"""


@pytest.mark.skip(reason="feat/render 브랜치에서 구현")
def test_line_length_limit():
    """자막 줄당 글자수 제한"""


@pytest.mark.skip(reason="feat/render 브랜치에서 구현")
def test_final_srt_timecodes():
    """최종 SRT 타임코드 정확성"""
