FROM python:3.12-slim

# ffmpeg 설치 + git (whisperx pip 설치에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch (CPU) 먼저 설치
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# WhisperX 설치
RUN pip install --no-cache-dir whisperx

# 프로젝트 의존성
COPY pyproject.toml .
COPY submark/ submark/
RUN pip install --no-cache-dir -e .

# 데이터 디렉토리
RUN mkdir -p /data/input /data/output

ENTRYPOINT ["submark"]
CMD ["--help"]
