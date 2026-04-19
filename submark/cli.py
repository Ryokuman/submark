"""Typer CLI 진입점"""

import typer

app = typer.Typer(name="submark", help="자막 + 편집 마커 자동 생성 도구")


@app.command()
def transcribe(
    input_path: str = typer.Argument(..., help="입력 영상 파일 경로"),
    lang: str = typer.Option("tr", "--lang", "-l", help="STT 언어"),
    output_dir: str = typer.Option("output", "--output", "-o", help="출력 디렉토리"),
) -> None:
    """영상 → transcript.json + subtitle.srt"""
    typer.echo(f"[transcribe] {input_path} (lang={lang}) → {output_dir}/")
    raise typer.Exit(code=1)  # TODO: v0.0.1 구현


@app.command()
def analyze(
    transcript_path: str = typer.Argument(..., help="transcript.json 경로"),
    output_dir: str = typer.Option("output", "--output", "-o", help="출력 디렉토리"),
) -> None:
    """transcript → markers (highlight/cut/chapter)"""
    typer.echo(f"[analyze] {transcript_path} → {output_dir}/")
    raise typer.Exit(code=1)  # TODO: v0.0.2 구현


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
