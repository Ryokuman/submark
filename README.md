# SubMark

터키어 팟캐스트/브이로그용 자막(SRT) + 편집 마커(Premiere CSV) 자동 생성 도구.

## 설치

```bash
pip install -e ".[stt,dev]"
```

## CLI 사용법

```bash
submark transcribe input.mp4 --lang tr -o output/
```

생성물:
- `output/transcript.json` — 전사 결과 (세그먼트, 단어 타임스탬프, 화자 분리)
- `output/subtitle.srt` — SRT 자막 파일

### 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--lang`, `-l` | `tr` | STT 언어 |
| `--output`, `-o` | `output` | 출력 디렉토리 |

## API 사용법

Python에서 직접 import하여 사용할 수 있습니다.

### 전체 파이프라인

```python
from pathlib import Path
from submark.transcribe import transcribe_pipeline

transcript = transcribe_pipeline(
    input_path=Path("input.mp4"),
    output_dir=Path("output/"),
    language="tr",
)
```

### 개별 함수

```python
from pathlib import Path
from submark.transcribe import extract_audio, run_whisperx, parse_whisperx_output
from submark.exporters.srt import write_srt

# 1. 오디오 추출
wav = extract_audio(Path("input.mp4"), Path("audio.wav"))

# 2. WhisperX 실행
raw = run_whisperx(
    wav,
    language="tr",
    model_size="large-v3",
    diarize=True,
    min_speakers=2,
    max_speakers=3,
)

# 3. Transcript 스키마로 변환
transcript = parse_whisperx_output(raw, source="input.mp4")

# 4. SRT 파일 생성
write_srt(transcript, Path("subtitle.srt"))
```

### 파라미터

`run_whisperx` 파라미터:

| 파라미터 | 기본값 | 환경변수 | 설명 |
|---|---|---|---|
| `language` | `"tr"` | `SUBMARK_LANGUAGE` | STT 언어 |
| `model_size` | `"large-v3"` | `SUBMARK_MODEL_SIZE` | Whisper 모델 크기 |
| `diarize` | `True` | `SUBMARK_DIARIZE` | 화자 분리 여부 |
| `min_speakers` | `None` | `SUBMARK_MIN_SPEAKERS` | 최소 화자 수 힌트 |
| `max_speakers` | `None` | `SUBMARK_MAX_SPEAKERS` | 최대 화자 수 힌트 |
| `compute_type` | `"auto"` | `SUBMARK_COMPUTE_TYPE` | 연산 정밀도 (float16, int8 등) |

`parse_whisperx_output` 파라미터:

| 파라미터 | 기본값 | 환경변수 | 설명 |
|---|---|---|---|
| `min_confidence` | `0.0` | `SUBMARK_MIN_CONFIDENCE` | 최소 confidence 임계값 |
| `merge_threshold` | `0.0` | `SUBMARK_MERGE_THRESHOLD` | 세그먼트 병합 간격 (초) |

모든 파라미터는 **함수 인자 > 환경변수 > 기본값** 순서로 적용됩니다.

## 테스트

```bash
pytest tests/ -v
```
