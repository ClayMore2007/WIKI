---
name: douyin-video-content
description: Use when a user asks to extract, transcribe, summarize, organize, convert, or save readable notes from an accessible Douyin/TikTok China video URL, share page, downloaded Douyin MP4, or Douyin video metadata.
---

# 抖音视频内容提取

## 概览

用于把可访问的抖音视频整理成可读文本。流程会结合网页元数据、可选的视频下载、语音转写和人工整理式摘要。

输出必须被视为“机器辅助提取结果”：不确定的公司名、数字、专有名词要标注“需核验”；金融、医疗、法律等高风险内容不能当作已验证事实。

## 边界

- 只处理公开视频，或用户明确有权访问、下载、转写的内容。
- 不绕过登录、私密权限、付费权限、验证码或反滥用机制。
- 先尝试提取官方分享页里的公开数据，再考虑下载媒体文件。
- 不去水印，不隐藏来源，除非用户确认有权这样处理。
- 如果视频内容涉及投资，明确说明“视频内容不构成投资建议”。

## 快速流程

1. 识别视频 ID。`https://www.douyin.com/video/<id>` 可以同时尝试 `https://www.douyin.com/share/video/<id>`。
2. 用 iPhone Safari User-Agent 抓取移动端分享页。
3. 从页面里的 `window._ROUTER_DATA` 解析 `videoInfoRes.item_list[0]`。
4. 提取基础信息：标题/描述、作者昵称、作者简介、发布时间、视频时长、话题标签、点赞/评论/分享/收藏数、封面地址、播放地址。
5. 如果用户需要“视频里说了什么”，只在可合法访问时下载 MP4。
6. 如果可用，使用 Whisper 或 `faster-whisper` 转写语音，保存带时间戳的原始转写稿和 JSON 分段。
7. 转写稿应转成 `_transcript.md`，包含 frontmatter、来源、风险提示和原始转写正文，作为 raw 层长期保留文件。
8. MP4 只作为临时中间产物；Markdown 转写稿和分段 JSON 保存后删除 MP4。若转写失败，也删除不完整 MP4，并记录失败原因。
9. 生成 Markdown 整理稿，建议包含：
   - 原链接和基础信息
   - 核心观点
   - 分段摘要
   - 重要名单、数字、时间点
   - 识别不确定处
   - 来源和风险提示

## 可复用脚本

优先使用脚本：

```powershell
python "Tools-工具/video/抖音视频内容提取/scripts/extract_douyin.py" "https://www.douyin.com/video/7636751736606133504" --out-dir "ClayMore/80-raw-原始资料/视频提取示例" --download --transcribe
```

常用模式：

只提取元数据：

```powershell
python "Tools-工具/video/抖音视频内容提取/scripts/extract_douyin.py" "<抖音链接>" --out-dir .
```

提取元数据并下载可访问 MP4：

```powershell
python "Tools-工具/video/抖音视频内容提取/scripts/extract_douyin.py" "<抖音链接>" --out-dir . --download
```

下载并转写：

```powershell
python "Tools-工具/video/抖音视频内容提取/scripts/extract_douyin.py" "<抖音链接>" --out-dir . --download --transcribe --model base
```

脚本会生成：

- `<id>_metadata.json`：视频元数据
- `<id>.mp4`：下载的视频，只有使用 `--download` 时生成；转写完成后应删除，不作为 raw 长期保存
- `<id>_transcript.md`：带时间戳的原始转写稿，作为 raw 层长期保留文件。若脚本先生成 `.txt`，应立即转换为 `.md` 并删除 `.txt`
- `<id>_segments.json`：结构化转写分段
- `<id>_notes_template.md`：整理稿模板

如果缺少 `faster-whisper`，并且适合在当前机器安装依赖，可以执行：

```powershell
python -m pip install faster-whisper imageio-ffmpeg
```

## 整理规则

- 可以根据上下文修正明显的语音识别错误，例如“一季度”被识别成“一级度”。
- 不确定的公司名、人名、产品名、股票名、金额，要标注“需核验”。
- 保留关键数字、时间点和视频中的因果判断。
- 金融类视频要区分“视频声称”和“已核验事实”。除非用户要求核验，否则不要把视频说法包装成事实。
- 最终回复里给出整理稿和原始转写稿的文件链接，不要把很长的全文直接塞进聊天窗口。

## 常见问题

| 问题 | 处理方式 |
| --- | --- |
| `www.douyin.com/video/...` 只返回脚本或空页面 | 尝试 `/share/video/<id>`，并使用移动端 User-Agent。 |
| 接口返回 `encrypt_data_miss` | 不尝试破解签名；改用分享页 SSR 数据，或请用户提供已授权下载的视频文件。 |
| MP4 下载不完整 | 使用 HTTP Range 或 `curl -L -C -` 续传，并校验文件大小或可解码时长。 |
| 转写到一半停止 | 检查容器时长、音频流和实际下载大小；必要时续传或重新下载。 |
| 公司名/术语识别错误 | 在整理稿中标注“需核验”，必要时结合视频画面、字幕或官方资料二次确认。 |
