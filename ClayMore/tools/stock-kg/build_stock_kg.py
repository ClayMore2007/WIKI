#!/usr/bin/env python3
"""Build the ClayMore stock research knowledge graph.

The graph is generated from existing Markdown/Canvas stock notes. Markdown and
YAML cards are the durable source for the graph layer; the Canvas is only a
generated browsing surface.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


UPDATED = "2026-06-01"
STOCK_ROOT = Path("Wiki/10-股票投资")
GRAPH_DIR = STOCK_ROOT / "02-股票研究流" / "知识图谱"
THEME_DIR = GRAPH_DIR / "主题卡"
COMPANY_DIR = GRAPH_DIR / "公司卡"
INDEX_FILE = GRAPH_DIR / "图谱索引.md"
CANVAS_FILE = GRAPH_DIR / "股票研究知识图谱.canvas"
COMPANY_CSV = STOCK_ROOT / "02-股票研究流" / "基础数据" / "A股公司名称库.csv"


THEME_RULES: dict[str, list[str]] = {
    "AI算力链": ["AI算力", "算力", "AIDC", "数据中心", "服务器", "超节点", "CSP", "CAPEX", "Token"],
    "国产算力": ["国产算力", "昇腾", "海光", "寒武纪", "华为", "国产AI", "ASIC"],
    "半导体": ["半导体", "芯片", "晶圆", "海思", "麒麟", "制程", "模拟芯片"],
    "先进封装": ["先进封装", "封测", "封装", "3D堆叠", "Chiplet", "HBM", "HBF"],
    "半导体材料": ["半导体材料", "先进封装材料", "材料唯一性", "光刻胶", "硅片", "电子特气", "金刚石", "玻璃基板"],
    "光模块与CPO": ["光模块", "CPO", "硅光", "光芯片", "光互联", "800G", "1.6T"],
    "PCB与玻璃基板": ["PCB", "玻璃基板", "高端板", "载板", "HDI"],
    "液冷与数据中心电源": ["液冷", "IDC电源", "HVDC", "散热", "电源", "温控"],
    "机器人与物理AI": ["机器人", "物理AI", "自动驾驶", "执行器", "传感器"],
    "商业航天": ["商业航天", "卫星", "火箭", "星链", "航天"],
    "创新药": ["创新药", "医药", "药企", "临床", "CXO"],
    "财报业绩": ["财报", "一季报", "业绩王者", "业绩反转", "归母净利润"],
    "交易方法": ["交易方法", "买入法", "量价", "尾盘", "情绪周期", "风控", "择时", "模式体系", "个人交易原则"],
    "宏观流动性": ["宏观流动性", "宏观", "流动性", "利率", "汇率"],
    "持仓与自选": ["持仓", "自选", "买入候选", "处理清单", "关注清单"],
}

LOW_CONFIDENCE_HINTS = ["confidence: low", "低置信", "短视频", "社交媒体", "抖音", "小红书", "来源声称"]
PENDING_HINTS = ["待核验", "未核验", "未证实", "需核验", "pending", "source_claim", "来源声称"]
COUNTER_HINTS = ["风险", "反证", "未证实", "低置信", "不构成投资建议", "不能", "尚未", "待核验"]
CLAIM_HINTS = ["认为", "推动", "受益", "核心", "逻辑", "结论", "来源声称", "订单", "CAPEX", "弹性", "景气"]


@dataclass
class Company:
    code: str
    raw_code: str
    market: str
    name: str


@dataclass
class SourceDoc:
    path: Path
    title: str
    text: str
    frontmatter: dict[str, str]
    confidence: str
    themes: set[str] = field(default_factory=set)
    companies: set[str] = field(default_factory=set)
    claims: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    verification_status: str = "pending_verification"

    @property
    def wiki_link(self) -> str:
        return str(self.path.with_suffix("")).replace("\\", "/")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip("\r\n")
    data: dict[str, str] = {}
    current_key = ""
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_\-]+:", line):
            key, value = line.split(":", 1)
            current_key = key.strip()
            data[current_key] = value.strip().strip('"')
        elif current_key:
            data[current_key] += " " + line.strip()
    return data, body


def markdown_title(path: Path, body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def load_companies(root: Path) -> dict[str, Company]:
    companies: dict[str, Company] = {}
    csv_path = root / COMPANY_CSV
    if not csv_path.exists():
        return companies
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            code = (row.get("code") or "").strip()
            if not name or len(name) < 2 or "�" in name:
                continue
            companies[name] = Company(
                code=code,
                raw_code=(row.get("raw_code") or "").strip(),
                market=(row.get("market") or "").strip(),
                name=name,
            )
    return companies


def iter_stock_files(root: Path) -> Iterable[Path]:
    stock_root = root / STOCK_ROOT
    graph_root = root / GRAPH_DIR
    for suffix in ("*.md", "*.canvas"):
        for path in stock_root.rglob(suffix):
            if graph_root in path.parents:
                continue
            if "ClayMore-Private-Wiki" in path.parts:
                continue
            yield path


def detect_themes(text: str, path: Path) -> set[str]:
    haystack = f"{path.as_posix()}\n{text}"
    themes = {theme for theme, keys in THEME_RULES.items() if any(key in haystack for key in keys)}
    return themes or {"其他股票资料"}


def detect_companies(text: str, path: Path, companies: dict[str, Company]) -> set[str]:
    found: list[tuple[int, int, str]] = []
    haystack = f"{path.stem}\n{text}"
    for name, company in companies.items():
        score = 0
        if len(name) >= 3 and name in haystack:
            score += haystack.count(name)
        if company.code and company.code in haystack:
            score += 2
        if company.raw_code and re.search(rf"(?<!\d){re.escape(company.raw_code)}(?!\d)", haystack):
            score += 1
        if score:
            found.append((score, len(name), name))
    found.sort(reverse=True)
    return {name for _, _, name in found[:40]}


def clean_line(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"\s+", " ", line).strip()
    line = line.strip("|-#*` ")
    return line


def extract_lines(text: str, hints: list[str], limit: int = 8) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if len(line) < 12 or len(line) > 220:
            continue
        if any(hint in line for hint in hints):
            if line not in lines:
                lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def confidence_from(frontmatter: dict[str, str], text: str) -> str:
    confidence = frontmatter.get("confidence", "").strip()
    if confidence:
        return confidence
    lowered = text.lower()
    if any(hint.lower() in lowered for hint in LOW_CONFIDENCE_HINTS):
        return "low"
    return "medium-low"


def verification_from(text: str, confidence: str) -> str:
    if confidence == "low" or any(hint in text for hint in PENDING_HINTS):
        return "pending_verification"
    if "已核验" in text or "verified" in text:
        return "partially_verified"
    return "source_claim"


def build_sources(root: Path, companies: dict[str, Company]) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for path in sorted(iter_stock_files(root)):
        text = read_text(path)
        if path.suffix == ".canvas":
            title = path.stem
            frontmatter: dict[str, str] = {}
            body = text[:12000]
        else:
            frontmatter, body = split_frontmatter(text)
            title = markdown_title(path.relative_to(root), body)
        rel_path = path.relative_to(root)
        confidence = confidence_from(frontmatter, text)
        doc = SourceDoc(
            path=rel_path,
            title=title,
            text=body,
            frontmatter=frontmatter,
            confidence=confidence,
        )
        doc.themes = detect_themes(body, rel_path)
        doc.companies = detect_companies(body, rel_path, companies)
        doc.claims = extract_lines(body, CLAIM_HINTS)
        doc.counter_evidence = extract_lines(body, COUNTER_HINTS)
        doc.verification_status = verification_from(body, confidence)
        docs.append(doc)
    return docs


def yaml_scalar(value: str) -> str:
    value = value.replace('"', '\\"')
    return f'"{value}"'


def yaml_list(values: Iterable[str], indent: str = "") -> str:
    items = list(values)
    if not items:
        return "[]"
    return "\n" + "\n".join(f"{indent}- {yaml_scalar(item)}" for item in items)


def slug(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\n\r\t]+', "-", value).strip(" .-")
    return value[:80] or "未命名"


def stable_id(*parts: str) -> str:
    raw = "::".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def rel_link(path: Path) -> str:
    return str(path.with_suffix("")).replace("\\", "/")


def card_link(path: Path) -> str:
    return f"[[{rel_link(path)}]]"


def top_counts(counts: Counter[str], limit: int | None = None) -> list[tuple[str, int]]:
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return items if limit is None else items[:limit]


def write_if_changed(path: Path, content: str, dry_run: bool) -> bool:
    if path.exists() and read_text(path) == content:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return True


def theme_card(theme: str, docs: list[SourceDoc], company_counts: Counter[str]) -> str:
    claims = []
    counters = []
    pending = []
    evidence = []
    for doc in docs:
        evidence.append(f"[[{doc.wiki_link}|{doc.title}]]")
        claims.extend(doc.claims[:2])
        counters.extend(doc.counter_evidence[:2])
        if doc.verification_status == "pending_verification":
            pending.append(f"[[{doc.wiki_link}|{doc.title}]]")
    companies = [name for name, _ in top_counts(company_counts, 25)]
    confidence = "low" if any(doc.confidence == "low" for doc in docs) else "medium-low"
    body_claims = claims[:12] or ["待从来源页继续提炼核心主张。"]
    body_counters = counters[:12] or ["待补充反证、风险和失效条件。"]
    body_pending = pending[:12]
    content = f"""---
type: theme
status: active
confidence: {confidence}
updated: {UPDATED}
themes:{yaml_list([theme], "  ")}
claims:{yaml_list(body_claims, "  ")}
companies:{yaml_list(companies, "  ")}
evidence:{yaml_list(evidence[:20], "  ")}
counter_evidence:{yaml_list(body_counters, "  ")}
open_questions:{yaml_list(["哪些来源声称能被公告、财报、招标或高质量研报交叉验证？", "哪些公司只是概念映射，哪些公司已有收入/订单/客户证据？"], "  ")}
---

# {theme}

> 自动生成的产业主题卡。低置信资料只作为研究线索，不构成投资建议，也不会自动进入买卖判断。

## 核心主张

{bullet_list(body_claims)}

## 相关公司

{table_companies(company_counts)}

## 证据来源

{bullet_list(evidence[:20])}

## 反证 / 风险

{bullet_list(body_counters)}

## 待核验入口

{bullet_list(body_pending or ["暂无单独标记的待核验来源。"])}
"""
    return content


def company_card(name: str, company: Company | None, docs: list[SourceDoc], themes: Counter[str]) -> str:
    evidence = [f"[[{doc.wiki_link}|{doc.title}]]" for doc in docs[:25]]
    claims = []
    counters = []
    for doc in docs:
        claims.extend(doc.claims[:1])
        counters.extend(doc.counter_evidence[:1])
    code = company.code if company else ""
    market = company.market if company else ""
    content = f"""---
type: company
status: active
confidence: medium-low
updated: {UPDATED}
ticker: {yaml_scalar(code)}
market: {yaml_scalar(market)}
themes:{yaml_list([theme for theme, _ in top_counts(themes, 12)], "  ")}
portfolio_status: "unknown"
research_status: "auto_collected"
bull_case:{yaml_list(claims[:8] or ["待从主题卡和来源页继续提炼正向逻辑。"], "  ")}
bear_case:{yaml_list(counters[:8] or ["待补充反证、风险和估值约束。"], "  ")}
evidence_links:{yaml_list(evidence, "  ")}
decision_links: []
---

# {name}

> 自动生成的公司卡。低置信资料只作为研究线索，不构成投资建议；这里只聚合研究线索，不自动生成买入、卖出或持仓处理结论。

## 基础信息

| 字段 | 值 |
|---|---|
| 代码 | {code or "待补"} |
| 市场 | {market or "待补"} |
| 研究状态 | auto_collected |

## 关联主题

{bullet_list([card_link(THEME_DIR / f"{slug(theme)}.md") for theme, _ in top_counts(themes, 12)])}

## 正向逻辑

{bullet_list(claims[:8] or ["待从主题卡和来源页继续提炼正向逻辑。"])}

## 反证 / 风险

{bullet_list(counters[:8] or ["待补充反证、风险和估值约束。"])}

## 证据来源

{bullet_list(evidence)}
"""
    return content


def bullet_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def table_companies(counts: Counter[str]) -> str:
    if not counts:
        return "暂无自动识别到的公司。"
    rows = ["| 公司 | 出现次数 | 公司卡 |", "|---|---:|---|"]
    for name, count in top_counts(counts, 25):
        rows.append(f"| {name} | {count} | {card_link(COMPANY_DIR / f'{slug(name)}.md')} |")
    return "\n".join(rows)


def index_page(docs: list[SourceDoc], theme_docs: dict[str, list[SourceDoc]], company_docs: dict[str, list[SourceDoc]]) -> str:
    low_docs = [doc for doc in docs if doc.confidence == "low"][:30]
    pending_docs = [doc for doc in docs if doc.verification_status == "pending_verification"][:30]
    theme_rows = ["| 产业主题 | 来源数 | 公司数 | 主题卡 |", "|---|---:|---:|---|"]
    for theme, items in sorted(theme_docs.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        companies = set().union(*(doc.companies for doc in items)) if items else set()
        theme_rows.append(f"| {theme} | {len(items)} | {len(companies)} | {card_link(THEME_DIR / f'{slug(theme)}.md')} |")
    company_rows = ["| 公司 | 来源数 | 关联主题 | 公司卡 |", "|---|---:|---|---|"]
    company_theme_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for company, items in company_docs.items():
        for doc in items:
            company_theme_counts[company].update(sorted(doc.themes))
    for company, items in sorted(company_docs.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:80]:
        themes = "、".join(theme for theme, _ in top_counts(company_theme_counts[company], 5))
        company_rows.append(f"| {company} | {len(items)} | {themes} | {card_link(COMPANY_DIR / f'{slug(company)}.md')} |")
    content = f"""---
type: stock_knowledge_graph_index
status: active
confidence: medium-low
updated: {UPDATED}
sources:
  - "[[Wiki/10-股票投资/股票投资总控台]]"
---

# 股票研究知识图谱

> 自动生成入口。Markdown/YAML 是真实数据底座，Canvas 是浏览层；低置信资料只进入研究图谱，不自动进入买卖判断。

## Canvas 入口

- [[Wiki/10-股票投资/02-股票研究流/知识图谱/股票研究知识图谱.canvas|股票研究知识图谱.canvas]]

## 产业主题

{chr(10).join(theme_rows)}

## 公司索引

{chr(10).join(company_rows)}

## 待核验资料

{bullet_list([f'[[{doc.wiki_link}|{doc.title}]] - {doc.verification_status}' for doc in pending_docs])}

## 低置信来源

{bullet_list([f'[[{doc.wiki_link}|{doc.title}]] - confidence: {doc.confidence}' for doc in low_docs])}

## 使用规则

- 资料先进入主题卡，再映射到公司卡。
- `confidence: low` 或 `pending_verification` 只作为线索，不能直接进入买入或卖出判断。
- 交易动作仍以人工确认后的 [[Wiki/10-股票投资/03-交易判断/买入候选清单]]、[[Wiki/10-股票投资/03-交易判断/持仓处理清单]] 和 [[Wiki/10-股票投资/03-交易判断/最终判断记录]] 为准。
"""
    return content


def canvas_json(theme_docs: dict[str, list[SourceDoc]], company_docs: dict[str, list[SourceDoc]]) -> str:
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    center_id = stable_id("center", "stock-kg")
    nodes.append(
        {
            "id": center_id,
            "type": "text",
            "text": "股票研究知识图谱\n主题 -> 主张 -> 证据/反证 -> 公司\n低置信资料不自动进入交易判断",
            "x": 0,
            "y": 0,
            "width": 360,
            "height": 140,
        }
    )
    themes = sorted(theme_docs, key=lambda theme: (-len(theme_docs[theme]), theme))
    radius = 760
    theme_positions: dict[str, tuple[int, int, str]] = {}
    for i, theme in enumerate(themes):
        angle = (2 * math.pi * i / max(len(themes), 1)) - math.pi / 2
        x = int(math.cos(angle) * radius)
        y = int(math.sin(angle) * radius)
        node_id = stable_id("theme", theme)
        theme_positions[theme] = (x, y, node_id)
        nodes.append(
            {
                "id": node_id,
                "type": "file",
                "file": str(THEME_DIR / f"{slug(theme)}.md").replace("\\", "/"),
                "x": x,
                "y": y,
                "width": 320,
                "height": 80,
            }
        )
        edges.append({"id": stable_id("edge", "center", theme), "fromNode": center_id, "toNode": node_id})
    company_theme_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for company, docs in company_docs.items():
        for doc in docs:
            company_theme_counts[company].update(sorted(doc.themes))
    placed = 0
    for company, docs in sorted(company_docs.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:60]:
        main_theme = top_counts(company_theme_counts[company], 1)[0][0] if company_theme_counts[company] else "其他股票资料"
        tx, ty, theme_id = theme_positions.get(main_theme, (0, 0, center_id))
        offset_x = ((placed % 5) - 2) * 180
        offset_y = 150 + ((placed // 5) % 4) * 110
        node_id = stable_id("company", company)
        nodes.append(
            {
                "id": node_id,
                "type": "file",
                "file": str(COMPANY_DIR / f"{slug(company)}.md").replace("\\", "/"),
                "x": tx + offset_x,
                "y": ty + offset_y,
                "width": 240,
                "height": 70,
            }
        )
        edges.append({"id": stable_id("edge", main_theme, company), "fromNode": theme_id, "toNode": node_id})
        placed += 1
    return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2)


def build(root: Path, dry_run: bool) -> dict[str, int]:
    companies = load_companies(root)
    docs = build_sources(root, companies)
    theme_docs: dict[str, list[SourceDoc]] = defaultdict(list)
    company_docs: dict[str, list[SourceDoc]] = defaultdict(list)
    for doc in docs:
        for theme in sorted(doc.themes):
            theme_docs[theme].append(doc)
        for company in sorted(doc.companies):
            company_docs[company].append(doc)
    changed = 0
    expected_paths: set[Path] = set()
    company_theme_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for company, items in company_docs.items():
        for doc in items:
            company_theme_counts[company].update(sorted(doc.themes))
    for theme, items in theme_docs.items():
        counts = Counter(company for doc in items for company in sorted(doc.companies))
        path = root / THEME_DIR / f"{slug(theme)}.md"
        expected_paths.add(path)
        changed += write_if_changed(path, theme_card(theme, items, counts), dry_run)
    for name, items in company_docs.items():
        path = root / COMPANY_DIR / f"{slug(name)}.md"
        expected_paths.add(path)
        changed += write_if_changed(path, company_card(name, companies.get(name), items, company_theme_counts[name]), dry_run)
    expected_paths.add(root / INDEX_FILE)
    expected_paths.add(root / CANVAS_FILE)
    changed += write_if_changed(root / INDEX_FILE, index_page(docs, theme_docs, company_docs), dry_run)
    changed += write_if_changed(root / CANVAS_FILE, canvas_json(theme_docs, company_docs), dry_run)
    if not dry_run:
        for directory in (root / THEME_DIR, root / COMPANY_DIR):
            if directory.exists():
                for existing in directory.glob("*.md"):
                    if existing not in expected_paths:
                        existing.unlink()
                        changed += 1
    return {
        "source_docs": len(docs),
        "themes": len(theme_docs),
        "companies": len(company_docs),
        "low_confidence_docs": sum(1 for doc in docs if doc.confidence == "low"),
        "pending_docs": sum(1 for doc in docs if doc.verification_status == "pending_verification"),
        "changed_files": changed,
    }


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    graph_root = root / GRAPH_DIR
    if not (root / INDEX_FILE).exists():
        errors.append("missing index page")
    if not (root / CANVAS_FILE).exists():
        errors.append("missing canvas")
    for path in graph_root.rglob("*.md"):
        text = read_text(path)
        if "ClayMore-Private-Wiki" in text:
            errors.append(f"private wiki link found in {path}")
        if "低置信资料只作为研究线索" not in text and path.name != "图谱索引.md":
            errors.append(f"missing low-confidence disclaimer in {path}")
    if (root / CANVAS_FILE).exists():
        data = json.loads(read_text(root / CANVAS_FILE))
        ids = [node["id"] for node in data.get("nodes", [])]
        edge_ids = [edge["id"] for edge in data.get("edges", [])]
        if len(ids) != len(set(ids)):
            errors.append("duplicate canvas node ids")
        if len(edge_ids) != len(set(edge_ids)):
            errors.append("duplicate canvas edge ids")
        for node in data.get("nodes", []):
            file = node.get("file")
            if file and not (root / file).exists():
                errors.append(f"canvas file target missing: {file}")
    trade_pages = [
        root / STOCK_ROOT / "03-交易判断" / "买入候选清单.md",
        root / STOCK_ROOT / "03-交易判断" / "持仓处理清单.md",
    ]
    for page in trade_pages:
        if page.exists() and "知识图谱" in read_text(page):
            errors.append(f"trade decision page was modified with graph content: {page}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ClayMore stock research knowledge graph.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="ClayMore wiki root")
    parser.add_argument("--dry-run", action="store_true", help="scan and report changes without writing")
    parser.add_argument("--write", action="store_true", help="write generated graph files")
    parser.add_argument("--validate", action="store_true", help="validate generated graph files")
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / STOCK_ROOT).exists():
        raise SystemExit(f"stock root not found: {root / STOCK_ROOT}")
    if args.validate:
        errors = validate(root)
        if errors:
            print("validation: failed")
            for error in errors:
                print(f"- {error}")
            return 1
        print("validation: ok")
        return 0
    dry_run = args.dry_run or not args.write
    result = build(root, dry_run=dry_run)
    mode = "dry-run" if dry_run else "write"
    print(f"mode: {mode}")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
