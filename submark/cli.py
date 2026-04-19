"""Typer CLI 진입점"""

from pathlib import Path

import typer

app = typer.Typer(name="submark", help="자막 + 편집 마커 자동 생성 도구")


@app.command()
def transcribe(
    input_path: str = typer.Argument(..., help="입력 영상 파일 경로"),
    lang: str = typer.Option("tr", "--lang", "-l", help="STT 언어"),
    output_dir: str = typer.Option("output", "--output", "-o", help="출력 디렉토리"),
) -> None:
    """영상 → transcript.json + subtitle.srt"""
    from submark.transcribe import transcribe_pipeline

    input_file = Path(input_path)
    if not input_file.exists():
        typer.echo(f"오류: 파일을 찾을 수 없습니다: {input_path}", err=True)
        raise typer.Exit(code=1)

    out = Path(output_dir)
    typer.echo(f"[transcribe] {input_path} (lang={lang}) → {output_dir}/")
    transcript = transcribe_pipeline(input_file, out, language=lang)
    typer.echo(f"완료: {len(transcript.segments)}개 세그먼트, {len(transcript.metadata.speakers)}명 화자")


@app.command()
def analyze(
    transcript_path: str = typer.Argument(..., help="transcript.json 경로"),
    output_dir: str = typer.Option("output", "--output", "-o", help="출력 디렉토리"),
    model: str = typer.Option("gemma3", "--model", "-m", help="Ollama 모델 이름"),
    system_prompt: str = typer.Option(None, "--system-prompt", "-s", help="커스텀 시스템 프롬프트"),
) -> None:
    """transcript → markers (highlight/cut/chapter)"""
    from pathlib import Path
    from submark.analyze import analyze as run_analyze

    typer.echo(f"[analyze] {transcript_path} → {output_dir}/")
    markers = run_analyze(
        Path(transcript_path),
        Path(output_dir),
        model=model,
        system_prompt=system_prompt,
    )
    typer.echo(f"[analyze] 완료 — 마커 {len(markers.markers)}개 생성")


@app.command()
def render(
    transcript_path: str = typer.Argument(..., help="transcript.json 경로"),
    markers_path: str = typer.Argument(..., help="markers.json 경로"),
    output_dir: str = typer.Option("output", "--output", "-o", help="출력 디렉토리"),
) -> None:
    """transcript + markers → final.srt"""
    typer.echo(f"[render] {transcript_path} + {markers_path} → {output_dir}/")
    raise typer.Exit(code=1)  # TODO: v0.0.3 구현


if __name__ == "__main__":
    app()
