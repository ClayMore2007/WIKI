---
name: bilibili-video-content
description: Use when extracting metadata, subtitles, audio transcripts, or structured notes from accessible Bilibili video URLs.
---

# B 站视频内容提取

用于把可访问的 B 站视频整理成可读文本。优先获取公开视频 metadata 和字幕；没有字幕时，可下载音频并用 Whisper 转写。

## 边界

- 只处理公开视频，或用户明确有权访问、下载、转写的内容。
- 不绕过登录、付费权限、验证码或反滥用机制。
- 不把 metadata 当作完整视频内容。
- 机器转写内容必须标注需核验。

## 快速流程

1. 用 `yt-dlp --dump-json` 获取 metadata。
2. 检查 `subtitles` 和 `automatic_captions`。
3. 如果无字幕且需要深度内容，下载音频。
4. 用 `faster-whisper` 转写。
5. 生成 metadata、transcript、segments 和 notes_template。

## 可复用脚本

```powershell
python "Tools-工具/video/B站视频内容提取/scripts/extract_bilibili.py" "<B站链接>" --out-dir . --download-audio --transcribe --model base
```

只提取 metadata：

```powershell
python "Tools-工具/video/B站视频内容提取/scripts/extract_bilibili.py" "<B站链接>" --out-dir .
```

依赖：

```powershell
python -m pip install yt-dlp faster-whisper imageio-ffmpeg
```

## 输出

- `<id>_metadata.json`
- `<id>.m4a`
- `<id>_transcript.txt`
- `<id>_segments.json`
- `<id>_notes_template.md`

## 整理规则

- 保留作者、发布时间、时长、标签、互动数据。
- 转写稿中的工具名、人名、数字、流程步骤要标注需核验。
- 技术教程要优先整理成“流程、工具链、适用场景、限制、可复用步骤”。
