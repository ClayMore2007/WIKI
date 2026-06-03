#!/usr/bin/env python3
"""Extract accessible Bilibili video metadata, optional audio, and transcript."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_json(cmd: list[str]) -> dict[str, Any]:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def metadata(url: str) -> dict[str, Any]:
    return run_json([sys.executable, "-m", "yt_dlp", "--skip-download", "--dump-json", url])


def clean_metadata(info: dict[str, Any], source_url: str) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "uploader_id": info.get("uploader_id"),
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string"),
        "description": info.get("description"),
        "tags": info.get("tags") or [],
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "thumbnail": info.get("thumbnail"),
        "subtitles": info.get("subtitles") or {},
        "automatic_captions": info.get("automatic_captions") or {},
        "webpage_url": info.get("webpage_url"),
    }


def download_audio(url: str, out_dir: Path, video_id: str) -> Path:
    out_tmpl = str(out_dir / f"{video_id}.%(ext)s")
    ffmpeg_args: list[str] = []
    try:
        import imageio_ffmpeg

        ffmpeg_args = ["--ffmpeg-location", imageio_ffmpeg.get_ffmpeg_exe()]
    except Exception:
        ffmpeg_args = []
    subprocess.run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "m4a",
            *ffmpeg_args,
            "-o",
            out_tmpl,
            url,
        ],
        check=True,
    )
    audio = out_dir / f"{video_id}.m4a"
    if audio.exists():
        return audio
    candidates = sorted(out_dir.glob(f"{video_id}.*"))
    if not candidates:
        raise FileNotFoundError(f"No downloaded audio found for {video_id}")
    return candidates[0]


def fmt_ts(seconds: float) -> str:
    minutes = int(seconds // 60)
    sec = seconds - minutes * 60
    return f"{minutes:02d}:{sec:05.2f}"


def transcribe(media: Path, out_txt: Path, out_json: Path, model_name: str) -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Missing faster-whisper. Install with: python -m pip install faster-whisper imageio-ffmpeg"
        ) from exc

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(media), language="zh", vad_filter=True, beam_size=5)
    rows: list[dict[str, Any]] = []
    lines: list[str] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        rows.append({"start": seg.start, "end": seg.end, "text": text})
        lines.append(f"[{fmt_ts(seg.start)} - {fmt_ts(seg.end)}] {text}")
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(
        json.dumps(
            {"language": info.language, "duration": info.duration, "segments": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_notes_template(path: Path, meta: dict[str, Any], transcript_path: Path | None) -> None:
    transcript_line = f"- Raw transcript: {transcript_path.name}\n" if transcript_path else ""
    tags = "、".join(meta.get("tags") or [])
    path.write_text(
        f"""# Bilibili Video Notes

Source: {meta.get("source_url")}

## Metadata

- Video ID: {meta.get("id")}
- Title: {meta.get("title")}
- Uploader: {meta.get("uploader")}
- Upload date: {meta.get("upload_date")}
- Duration: {meta.get("duration_string") or meta.get("duration")}
- Tags: {tags}
- Views: {meta.get("view_count")}
- Likes: {meta.get("like_count")}
- Comments: {meta.get("comment_count")}

## Description

{meta.get("description") or ""}

## Core Thesis

TODO: Summarize the main claim in 1-3 sentences.

## Organized Notes

TODO: Convert transcript into sections. Preserve names, numbers, tools, and uncertainty markers.

## Files

- Metadata: {meta.get("id")}_metadata.json
{transcript_line}
## Caveat

This is machine-assisted extraction. ASR terms, tool names, and numbers may need verification.
""",
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--download-audio", action="store_true")
    parser.add_argument("--transcribe", action="store_true")
    parser.add_argument("--model", default="base")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    info = metadata(args.url)
    meta = clean_metadata(info, args.url)
    video_id = meta.get("id") or "bilibili"
    meta_path = out_dir / f"{video_id}_metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_path: Path | None = None
    transcript_path: Path | None = None
    if args.download_audio or args.transcribe:
        audio_path = download_audio(args.url, out_dir, video_id)

    if args.transcribe:
        assert audio_path is not None
        transcript_path = out_dir / f"{video_id}_transcript.txt"
        segments_path = out_dir / f"{video_id}_segments.json"
        transcribe(audio_path, transcript_path, segments_path, args.model)

    notes_path = out_dir / f"{video_id}_notes_template.md"
    write_notes_template(notes_path, meta, transcript_path)

    print(json.dumps({
        "metadata": str(meta_path),
        "audio": str(audio_path) if audio_path else None,
        "transcript": str(transcript_path) if transcript_path else None,
        "notes_template": str(notes_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
