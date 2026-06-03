#!/usr/bin/env python3
"""Extract accessible Douyin video metadata, optional media, and transcript."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)


@dataclass
class Extraction:
    video_id: str
    source_url: str
    item: dict[str, Any]


def request_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 60) -> bytes:
    req_headers = {"User-Agent": MOBILE_UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if headers:
        req_headers.update(headers)
    req = Request(url, headers=req_headers)
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return request_bytes(url).decode("utf-8", errors="replace")


def video_id_from_url(url: str) -> str:
    match = re.search(r"/(?:video|share/video)/(\d+)", url)
    if match:
        return match.group(1)
    parsed = urlparse(url)
    fallback = re.search(r"(\d{12,})", parsed.path + "?" + parsed.query)
    if fallback:
        return fallback.group(1)
    raise ValueError(f"Could not find a Douyin video id in URL: {url}")


def share_url(video_id: str) -> str:
    return f"https://www.douyin.com/share/video/{video_id}"


def parse_router_data(html: str) -> dict[str, Any]:
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if not match:
        raise ValueError("Could not find window._ROUTER_DATA in the share page.")
    return json.loads(match.group(1))


def find_item(router_data: dict[str, Any]) -> dict[str, Any]:
    loader = router_data.get("loaderData", {})
    for value in loader.values():
        if isinstance(value, dict):
            res = value.get("videoInfoRes")
            if isinstance(res, dict) and res.get("item_list"):
                return res["item_list"][0]
    raise ValueError("Could not find videoInfoRes.item_list[0] in router data.")


def extract(url: str) -> Extraction:
    vid = video_id_from_url(url)
    html = fetch_text(share_url(vid))
    item = find_item(parse_router_data(html))
    return Extraction(video_id=vid, source_url=url, item=item)


def clean_metadata(ext: Extraction) -> dict[str, Any]:
    item = ext.item
    author = item.get("author") or {}
    video = item.get("video") or {}
    music = item.get("music") or {}
    stats = item.get("statistics") or {}
    create_time = item.get("create_time")
    created_at = None
    if isinstance(create_time, (int, float)):
        created_at = datetime.fromtimestamp(create_time).isoformat(timespec="seconds")
    return {
        "video_id": ext.video_id,
        "source_url": ext.source_url,
        "desc": item.get("desc"),
        "created_at": created_at,
        "create_time": create_time,
        "author": {
            "nickname": author.get("nickname"),
            "short_id": author.get("short_id"),
            "signature": author.get("signature"),
        },
        "duration_ms": video.get("duration"),
        "width": video.get("width"),
        "height": video.get("height"),
        "statistics": {
            "digg_count": stats.get("digg_count"),
            "comment_count": stats.get("comment_count"),
            "share_count": stats.get("share_count"),
            "collect_count": stats.get("collect_count"),
        },
        "hashtags": [
            e.get("hashtag_name")
            for e in item.get("text_extra") or []
            if isinstance(e, dict) and e.get("hashtag_name")
        ],
        "music": {"title": music.get("title"), "author": music.get("author")},
        "cover_urls": ((video.get("cover") or {}).get("url_list") or []),
        "play_urls": ((video.get("play_addr") or {}).get("url_list") or []),
    }


def download_with_resume(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    start = output.stat().st_size if output.exists() else 0
    headers = {"Referer": "https://www.douyin.com/"}
    if start:
        headers["Range"] = f"bytes={start}-"
    req = Request(url, headers={"User-Agent": MOBILE_UA, **headers})
    try:
        with urlopen(req, timeout=120) as response:
            status = getattr(response, "status", None)
            if start and status == 200:
                start = 0
            mode = "ab" if start else "wb"
            expected_chunk_size = response.headers.get("Content-Length")
            expected_total_size = None
            if expected_chunk_size and expected_chunk_size.isdigit():
                expected_total_size = start + int(expected_chunk_size)
            with output.open(mode) as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            actual_size = output.stat().st_size
            if expected_total_size is not None and actual_size != expected_total_size:
                raise RuntimeError(
                    f"Incomplete download: expected {expected_total_size} bytes, got {actual_size} bytes"
                )
    except HTTPError as exc:
        if start and exc.code == 416:
            return
        raise


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


def write_notes_template(path: Path, metadata: dict[str, Any], transcript_path: Path | None) -> None:
    desc = metadata.get("desc") or ""
    author = (metadata.get("author") or {}).get("nickname") or ""
    created = metadata.get("created_at") or metadata.get("create_time") or ""
    hashtags = " ".join(f"#{h}" for h in metadata.get("hashtags") or [])
    transcript_line = f"- Raw transcript: {transcript_path.name}\n" if transcript_path else ""
    path.write_text(
        f"""# Douyin Video Notes

Source: {metadata.get("source_url")}

## Metadata

- Video ID: {metadata.get("video_id")}
- Author: {author}
- Created: {created}
- Description: {desc}
- Hashtags: {hashtags}

## Core Thesis

TODO: Summarize the main claim in 1-3 sentences.

## Organized Notes

TODO: Convert the transcript into sections. Preserve names, numbers, and uncertainty markers.

## Files

- Metadata: {metadata.get("video_id")}_metadata.json
{transcript_line}
## Caveat

This is machine-assisted extraction. Mark uncertain ASR terms as needing verification.
""",
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--transcribe", action="store_true")
    parser.add_argument("--model", default="base")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = extract(args.url)
    metadata = clean_metadata(ext)
    meta_path = out_dir / f"{ext.video_id}_metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    media_path: Path | None = None
    transcript_path: Path | None = None
    if args.download or args.transcribe:
        play_urls = metadata.get("play_urls") or []
        if not play_urls:
            raise SystemExit("No accessible play URL found in metadata.")
        media_path = out_dir / f"{ext.video_id}.mp4"
        download_with_resume(play_urls[0], media_path)

    if args.transcribe:
        assert media_path is not None
        transcript_path = out_dir / f"{ext.video_id}_transcript.txt"
        segments_path = out_dir / f"{ext.video_id}_segments.json"
        transcribe(media_path, transcript_path, segments_path, args.model)

    notes_path = out_dir / f"{ext.video_id}_notes_template.md"
    write_notes_template(notes_path, metadata, transcript_path)

    print(json.dumps({
        "metadata": str(meta_path),
        "media": str(media_path) if media_path else None,
        "transcript": str(transcript_path) if transcript_path else None,
        "notes_template": str(notes_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
