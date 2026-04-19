# SubMark — 설계 문서

> 터키어 팟캐스트/브이로그용 자막 + 편집 마커 생성 도구
> 설계 확정일: 2026-04-19
> 버전: v0.1 설계안

---

## 1. 프로젝트 개요

### 1.1 한 줄 정의
영상 파일을 입력받아 **자막(SRT)**과 **편집 마커(Premiere CSV)**를 자동 생성하는 로컬 도구.

### 1.2 탄생 배경
친구들과 함께 찍는 터키어 팟캐스트/브이로그의 편집 시간을 줄이는 것이 목표. 특히 다음 작업을 자동화:
- 어디가 재밌는지(하이라이트) 찾기
- 어디를 잘라야 하는지(NG, 정적, 말더듬) 찾기
- 주제별 구분(챕터) 표시
- 최종 영상에 박을 자막 생성

### 1.3 타겟 유저
- **v0**: 나 + 친구들 (비공개)
- **v1 이후**: 1인 영상 크리에이터 (오픈소스 공개 고려)

### 1.4 Non-Goals (명시적으로 안 할 것)
- 실시간 자막 생성
- 영상 렌더링 / 컷 편집
- 타임라인 편집 UI
- 클라우드 스토리지
- 사용자 계정/인증
- 모바일 네이티브 앱
- Premiere 플러그인 (CSV import로 충분)

---

## 2. 콘텐츠 특성 (중요)

### 2.1 언어 분포
- **터키어: 85~95%** (주 언어)
- **한국어: 5~10%** (설명/인용 시)
- **영어: ~5%** (기술 용어/고유명사)

→ **"다국어 처리"가 아니라 "터키어 중심 + 외국어 소수 섞임"** 문제로 정의함.

### 2.2 촬영 환경
- 카페 등 외부 로케이션 (브이로그 성격)
- 대화형 팟캐스트 (2~3인)
- 아이폰/안드로이드 혼용 → 포맷 섞임

---

## 3. 최종 아키텍처

```
[1] 영상 업로드 (MP4/MOV 등)
      ↓
[2] ffmpeg: 오디오 추출 (.wav, 16kHz mono)
      ↓
[3] WhisperX (--language tr, --diarize)
      - 터키어 고정 STT
      - 화자 분리 (pyannote)
      - 단어 단위 타임스탬프
      - 출력: transcript.json
      ↓ (WhisperX 언로드)
[4] Gemma 3 (Ollama, 로컬)
      - 한/영 음차 복원
      - 마커 분류 (highlight / cut / chapter)
      - 출력: markers.json
      ↓
[5] Export
      - SRT (자막)
      - CSV (Premiere 마커)
      - TXT (YouTube 챕터)
      - JSON (raw backup)
      ↓
[6] 다운로드
```

### 3.1 핵심 설계 원칙
1. **파일 기반 파이프라인**: 각 단계가 파일을 입출력 → 독립 실행/테스트 가능
2. **순차 모델 로딩**: M1 Pro 16GB 메모리 제약으로 WhisperX → Gemma 순차 실행
3. **터키어 고정 STT + LLM 후처리**: code-switching 해결책

---

## 4. 다국어 처리 전략

### 4.1 선택: "터키어 고정 + LLM 후처리"

**이유**: 오디오의 85%+ 가 터키어라 언어 감지 오버헤드가 불필요.

**동작 방식**:
1. WhisperX에 `--language tr` 고정
2. 한/영 부분은 음차로 찍힘 (예: "annyeonghaseyo", "thank you")
3. Gemma가 컨텍스트 보고 원래 언어로 복원 ("안녕하세요", "thank you")
4. 타임스탬프는 그대로 유지

### 4.2 대안 비교 (선택되지 않음)

| 전략 | 정확도 | 난이도 | 속도 | 선택? |
|---|---|---|---|---|
| **터키어 고정 + LLM 후처리** | ★★★★ | 쉬움 | 빠름 | ✓ |
| auto 언어 감지 | ★★ | 쉬움 | 빠름 | × |
| 화자별 언어 고정 | ★★★★★ | 어려움 | 느림 | × (셋 다 터키어 주사용) |
| 세그먼트별 재처리 | ★★★★ | 중간 | 매우 느림 | × |

### 4.3 검증 필요
실제 녹음 샘플 5~10분으로 Whisper 터키어 고정 테스트 → 한/영 섞인 부분이 **어떻게 찍히는지** 확인 필수. 음차가 너무 깨지면 전략 재검토.

---

## 5. 데이터 모델

### 5.1 Transcript (v0.0.1 출력)

```typescript
type Transcript = {
  metadata: {
    source: string          // "input.mp4"
    duration: number        // seconds
    language: "tr"
    speakers: string[]      // ["SPEAKER_00", "SPEAKER_01"]
    created_at: string      // ISO 8601
  }
  segments: Segment[]
}

type Segment = {
  id: string                // "seg_0001"
  start: number             // seconds
  end: number
  text: string              // 원본 터키어 (한/영은 음차)
  speaker: string
  words: Word[]
  confidence: number
}

type Word = {
  word: string
  start: number
  end: number
}
```

### 5.2 Markers (v0.0.2 출력)

```typescript
type Markers = {
  metadata: {
    transcript_id: string
    generated_by: string    // "gemma-3-..."
    created_at: string
  }
  markers: Marker[]
}

type Marker = {
  id: string                // "mk_0001"
  start: number
  end: number
  type: MarkerType
  reason: string            // "독일 이주 얘기, 친구 리액션 강함"
  confidence: number
  source_segments: string[] // ["seg_0042", "seg_0043"]
}

type MarkerType =
  | "highlight"   // 초록: 살릴 부분
  | "cut"         // 빨강: 제거할 부분
  | "chapter"     // 파랑: 주제 전환점
  | "silence"     // 노랑: 정적
```

### 5.3 Premiere CSV 포맷

```csv
Marker Name,Description,In,Out,Duration,Marker Type
"하이라이트: 독일 이주","친구 리액션 강함",00:05:23:12,00:06:47:03,00:01:23:21,Comment
"NG: 반복","같은 말 3번",00:12:15:00,00:12:22:10,00:00:07:10,Comment
```

**색상 매핑** (Premiere 마커 8색 활용):
- 🟢 초록 → highlight
- 🔴 빨강 → cut
- 🟡 노랑 → silence
- 🔵 파랑 → chapter

---

## 6. 기술 스택

### 6.1 확정 스택

| 레이어 | 기술 | 이유 |
|---|---|---|
| **언어 (백엔드)** | Python 3.12 | WhisperX, pyannote가 Python 강제 |
| **CLI 프레임워크** | Typer | 타입 힌트 기반, 모던 |
| **STT** | WhisperX (large-v3) | 다국어 + 화자분리 + 단어 타임스탬프 올인원 |
| **LLM** | Gemma 3 (Ollama) | 로컬, 최신 모델 |
| **영상 처리** | ffmpeg-python | 오디오 추출만 |
| **데이터 검증** | Pydantic | JSON 스키마 강제 |
| **실행 환경** | M1 Pro 16GB | 개발/운영 공통 |

### 6.2 v0.1.0 프론트 스택 (나중에)
- 확정 안 함. v0.0.3 이후 결정.
- 후보: FastAPI + 바닐라 HTML (극단 미니멀) / Vite + React (가벼움)
- **Next.js는 오버킬로 판단 → 사용 안 함**

### 6.3 검토했으나 선택하지 않은 것

- **Rust**: ML 생태계 빈약, 학습 비용 높음, 성능 병목 아님
- **Node.js 백엔드**: WhisperX를 subprocess로만 호출 가능 → 복잡도 증가
- **Next.js**: SSR 불필요, 페이지 2~3개 수준
- **Claude API**: "전부 로컬" 원칙 유지 위해 Gemma 선택
- **whisper.cpp**: 화자분리 별도 필요 → WhisperX 올인원이 단순

---

## 7. 버전 로드맵

### v0.0.1 — STT CLI

**목표**: 영상 → 자막 생성

```bash
submark transcribe input.mp4 --lang tr -o output/
```

**생성물**:
- `output/transcript.json` (raw, 이후 단계의 입력)
- `output/subtitle.srt`

**구현 범위**:
- WhisperX 래핑
- 터키어 고정 (`--language tr`)
- 화자 분리 포함
- JSON 스키마 확정
- SRT writer

---

### v0.0.2 — 분석 CLI

**목표**: 자막 → 하이라이트/편집점/챕터 추출

```bash
submark analyze output/transcript.json -o output/
```

**생성물**:
- `output/markers.json`
- `output/markers.csv` (Premiere import용)
- `output/chapters.txt` (YouTube 설명란용)

**구현 범위**:
- Gemma 3 프롬프트 설계
- 마커 분류 로직 (highlight / cut / chapter)
- Premiere CSV writer (색상 매핑)
- YouTube 챕터 writer

---

### v0.0.3 — 최종 자막 CLI

**목표**: 편집된 영상에 박을 자막 생성

```bash
submark render-subtitle output/transcript.json output/markers.json -o output/
```

**생성물**:
- `output/final.srt` (cut 구간 제외, 한/영 복원)

**구현 범위**:
- `cut` 마커 구간 제거
- Gemma로 한/영 음차 복원
- 자막 스타일 적용 (줄당 글자수 제한 등)

**주의**: 이 단계 기준 "편집은 직접 함" 전제. SubMark는 자막만 주고, Premiere 등으로 영상 컷은 사용자가 직접.

---

### v0.1.0 — 통합 + 웹 UI

**목표**: CLI 3단계를 웹에서 한 번에 실행

```bash
submark serve --port 8000
```

**구현 범위**:
- FastAPI 서버
- 업로드 → 자동 파이프라인 실행
- 폴링 기반 진행률
- 결과 zip 다운로드
- 프론트 (형태 미정)

---

## 8. 프로젝트 구조

```
submark/
├── pyproject.toml
├── README.md
├── SUBMARK_DESIGN.md        # (이 문서)
├── submark/
│   ├── __init__.py
│   ├── cli.py               # Typer 진입점
│   ├── transcribe.py        # v0.0.1: WhisperX 래퍼
│   ├── analyze.py           # v0.0.2: Gemma 분석
│   ├── render.py            # v0.0.3: 최종 자막 생성
│   ├── exporters/
│   │   ├── srt.py
│   │   ├── premiere_csv.py
│   │   └── youtube_chapter.py
│   ├── models.py            # Pydantic 스키마
│   └── llm.py               # Gemma/Ollama 래퍼
├── tests/
│   └── samples/             # 테스트용 샘플 영상
└── output/                  # 실행 결과 (gitignore)
```

---

## 9. 메모리 관리 (M1 Pro 16GB)

### 9.1 메모리 예산

| 항목 | 사용량 |
|---|---|
| macOS + 기본 앱 | ~4GB |
| WhisperX large-v3 | ~6GB |
| Gemma 3 (Q4) | ~6GB |
| **합계 (동시)** | **~16GB (한계)** |

### 9.2 전략: 순차 실행

```
[Phase 1] WhisperX 로드 → STT 실행 → 언로드
                                      ↓
[Phase 2] Gemma 로드 → 분석 실행 → 언로드
```

- CLI 단계가 분리되어 있어 자연스럽게 순차 실행됨
- v0.1.0 통합 시에도 Worker 프로세스를 분리해서 순차 호출

---

## 10. 검증/POC 체크리스트

구현 전 반드시 확인:

- [ ] 실제 팟캐스트 샘플(5~10분)로 WhisperX 터키어 고정 테스트
- [ ] 한/영 섞인 구간의 음차 품질 확인
- [ ] M1 Pro에서 WhisperX Metal(MPS) 지원 상태 확인 (CTranslate2 MPS 이슈 가능성)
- [ ] Gemma 3 최신 버전 + Ollama 셋업
- [ ] 화자분리 정확도 확인 (2~3인 대화)
- [ ] 메모리 사용량 실측 (16GB 한계 내 안정 동작 여부)

---

## 11. 다음 단계

1. 위 POC 체크리스트 실행
2. POC 결과에 따라 다국어 전략 최종 확정
3. v0.0.1 구현 (Claude Code로 진행)
4. 샘플 영상으로 반복 테스트 → JSON 스키마 fix
5. v0.0.2, v0.0.3 순차 진행

---

## 부록 A: 설계 의사결정 요약

| 결정 | 선택 | 대안 | 선택 이유 |
|---|---|---|---|
| STT 엔진 | WhisperX | whisper.cpp | 화자분리 올인원 |
| LLM | Gemma 3 (로컬) | Claude API | "전부 로컬" 원칙 |
| 다국어 처리 | 터키어 고정 + LLM 후처리 | 화자별 고정 / auto | 오디오 85%+ 터키어 |
| 백엔드 언어 | Python | TypeScript / Rust | ML 생태계 |
| 프론트 프레임워크 | 미정 (v0.1.0에서 결정) | Next.js | 오버킬 |
| 배포 방식 | CLI → 웹서버 순차 배포 | 일괄 | 점진 검증 |
| 아키텍처 | 파일 기반 파이프라인 | 단일 모놀리스 | 독립 테스트/디버깅 |

## 부록 B: 폐기된 아이디어

- **실시간 자막**: 촬영 UX에 도움 안 됨, 모바일 large 모델 불가, 다국어 정확도 이슈
- **타임라인 편집 UI**: 스코프 과다, 편집은 Premiere 등으로 충분
- **영상 렌더링**: 스코프 과다, ffmpeg concat 복잡도
- **Premiere 플러그인 (CEP/UXP)**: CSV import로 충분
- **모바일 앱**: 서버 배포 + 웹 접근으로 대체
