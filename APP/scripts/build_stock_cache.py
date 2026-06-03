from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI_ROOT = APP_ROOT.parent / "ClayMore"
STOCK_ROOT = Path("Wiki/10-股票投资")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), APP_ROOT)).as_posix()
    except ValueError:
        return path.as_posix()


def slug(value: str) -> str:
    cleaned = re.sub(r"\s+", "-", value.strip())
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", cleaned)
    return cleaned.strip("-").lower() or "unknown"


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    index = 0
    while index < len(lines) - 1:
        header_parts = split_table_line(lines[index])
        separator_parts = split_table_line(lines[index + 1])
        if not header_parts or not all(is_separator_cell(cell) for cell in separator_parts):
            index += 1
            continue
        index += 2
        while index < len(lines):
            parts = split_table_line(lines[index])
            if len(parts) != len(header_parts):
                break
            if all(is_separator_cell(cell) for cell in parts):
                index += 1
                continue
            rows.append(dict(zip(header_parts, parts)))
            index += 1
        continue
    return rows


def split_table_line(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def is_separator_cell(cell: str) -> bool:
    return bool(re.fullmatch(r":?-{3,}:?", cell.strip()))


def clean_company_name(value: str) -> str:
    value = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", value)
    value = re.sub(r"（自选缓存名：.*?）", "", value)
    value = re.sub(r"\(自选缓存名：.*?\)", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_int(value: str, default: int = 0) -> int:
    value = value.replace(",", "").strip()
    if not value or value == "--":
        return default
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else default


def parse_float(value: str) -> float | None:
    value = clean_company_name(value).replace(",", "").strip()
    if not value or value == "--":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_stock_quick_rows(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in parse_markdown_table(text):
        if not {"主线", "环节", "优先级", "公司", "代码"}.issubset(row):
            continue
        result.append(
            {
                "chain": row["主线"],
                "stage": row["环节"],
                "priority": row["优先级"],
                "company": clean_company_name(row["公司"]),
                "code": row["代码"].strip(),
                "heat": parse_int(row.get("资料热度", "0")),
                "note": row.get("备注", "").strip(),
            }
        )
    return result


def parse_frequency_rows(text: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in parse_markdown_table(text):
        if not {"公司名", "出现次数", "资料日期范围", "代表资料"}.issubset(row):
            continue
        company = clean_company_name(row["公司名"])
        result[company] = {
            "count": parse_int(row["出现次数"]),
            "sourceCount": parse_int(row.get("涉及资料数", "0")),
            "dateRange": row["资料日期范围"].strip(),
            "sourceRefs": parse_wikilinks(row["代表资料"]),
        }
    return result


def parse_wikilinks(text: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for link in re.findall(r"\[\[([^\]]+)\]\]", text):
        target, _, label = link.partition("|")
        refs.append({"target": target.strip(), "label": (label or target).strip()})
    return refs


def parse_watchlist_sections(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current_section = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_section in {"我的持仓", "自选股"}:
                items.extend(parse_watchlist_table(current_section, "\n".join(current_lines)))
            current_section = line.removeprefix("## ").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section in {"我的持仓", "自选股"}:
        items.extend(parse_watchlist_table(current_section, "\n".join(current_lines)))
    return items


def parse_watchlist_table(section: str, text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ownership_default = "持仓 + 自选" if section == "我的持仓" else "自选"
    for row in parse_markdown_table(text):
        if not {"代码", "名称"}.issubset(row):
            continue
        price = row.get("本地记录价格", row.get("现价", "--"))
        item = {
            "code": row["代码"].strip(),
            "name": clean_company_name(row["名称"]),
            "price": price.strip(),
            "priceDate": row.get("本地记录日期", "--").strip(),
            "market": row.get("市场代码", "").strip(),
            "ownership": row.get("归属", ownership_default).strip() or ownership_default,
            "note": row.get("备注", "").strip(),
        }
        items.append(item)
    return dedupe_by_code(items)


def dedupe_by_code(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        code = item.get("code", "")
        if code not in seen:
            seen[code] = item
        elif seen[code].get("ownership") == "自选" and "持仓" in item.get("ownership", ""):
            seen[code] = item
    return list(seen.values())


def parse_raw_snapshot(path: Path) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for row in parse_markdown_table(read_text(path)):
        code = row.get("代码")
        price = row.get("价格", row.get("本地记录价格", row.get("现价", "")))
        if not code or not price:
            continue
        number = parse_float(price)
        if number is not None:
            snapshot[code.strip()] = number
    return snapshot


def load_snapshots(wiki_root: Path) -> dict[str, dict[str, float]]:
    snapshots: dict[str, dict[str, float]] = {}
    for folder in ["同花顺自选股", "同花顺持仓板块"]:
        raw_dir = wiki_root / "80-raw-原始资料" / folder
        if not raw_dir.exists():
            continue
        for path in raw_dir.glob("同花顺*.md"):
            match = re.search(r"_(\d{8})\.md$", path.name)
            if match:
                date = match.group(1)
                snapshots.setdefault(date, {}).update(parse_raw_snapshot(path))
    return snapshots


def calculate_snapshot_change(
    code: str,
    current_price: str,
    current_date: str,
    snapshots: dict[str, dict[str, float]],
    days: int,
) -> dict[str, Any]:
    current = parse_float(current_price)
    if current is None or not re.fullmatch(r"\d{8}", current_date):
        return {"status": "本地快照不足"}
    target = datetime.strptime(current_date, "%Y%m%d") - timedelta(days=days)
    candidates = sorted(
        date for date, values in snapshots.items() if date <= current_date and code in values
    )
    prior_dates = [date for date in candidates if datetime.strptime(date, "%Y%m%d") <= target]
    if not prior_dates:
        return {"status": "本地快照不足"}
    from_date = prior_dates[-1]
    previous = snapshots[from_date][code]
    if previous == 0:
        return {"status": "本地快照不足"}
    return {
        "status": "ok",
        "fromDate": from_date,
        "percent": round((current - previous) / previous * 100, 2),
    }


def extract_company_card(path: Path) -> dict[str, Any]:
    text = read_text(path)
    summary = ""
    risks: list[str] = []
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped.removeprefix("## ").strip()
            continue
        if not summary and stripped and not stripped.startswith(("---", "#", "type:", "status:", "sources:", "tags:")):
            summary = re.sub(r"^[-*> ]+", "", stripped)
        if "风险" in section or "反证" in section:
            if stripped.startswith(("-", "|")) and not is_separator_cell(stripped.strip("|").split("|")[0].strip()):
                risks.append(stripped)
    return {
        "path": str(path),
        "summary": summary[:420],
        "risks": risks[:8],
        "sourceRefs": parse_wikilinks(text)[:12],
    }


def extract_source_file(path: Path, stock_root: Path) -> dict[str, Any]:
    title = path.stem
    date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", title)
    month = date_match.group(1)[:7] if date_match else "日期未知"
    text = read_text(path)
    companies = sorted(set(clean_company_name(name) for name in re.findall(r"<span[^>]*>(.*?)</span>", text)))
    rel = path.relative_to(stock_root).as_posix()
    return {"title": title, "month": month, "path": rel, "companies": companies}


def build_cache(wiki_root: Path, out_dir: Path) -> None:
    stock_root = wiki_root / STOCK_ROOT
    quick_path = stock_root / "02-股票研究流" / "板块优质股票速查表.md"
    stock_info_path = stock_root / "02-股票研究流" / "我的股票信息.md"
    frequency_path = stock_root / "01-Cubox资料流" / "公司名出现频率总表.md"
    cards_dir = stock_root / "02-股票研究流" / "知识图谱" / "公司卡"
    sources_dir = stock_root / "01-Cubox资料流" / "主题资料总结"

    quick_rows = parse_stock_quick_rows(read_text(quick_path))
    frequencies = parse_frequency_rows(read_text(frequency_path))
    watchlist_items = parse_watchlist_sections(read_text(stock_info_path))
    snapshots = load_snapshots(wiki_root)
    source_files = [extract_source_file(path, stock_root) for path in sources_dir.rglob("*.md")]

    companies = build_companies(quick_rows, frequencies, watchlist_items, cards_dir, stock_root)
    chains = build_industry_chains(quick_rows, source_files)
    watchlist = build_watchlist(watchlist_items, companies, snapshots)

    write_json(out_dir / "industry_chains.json", chains)
    write_json(out_dir / "companies.json", companies)
    write_json(out_dir / "watchlist.json", watchlist)
    write_json(out_dir / "sources.json", source_files)
    write_json(
        out_dir / "meta.json",
        {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "wikiRoot": display_path(wiki_root),
            "disclaimer": "本工具只用于个人观察和 Wiki 记录；本地价格不是实时行情；资料热度不等于投资建议、订单确认或业绩确认。",
        },
    )


def build_companies(
    quick_rows: list[dict[str, Any]],
    frequencies: dict[str, dict[str, Any]],
    watchlist_items: list[dict[str, Any]],
    cards_dir: Path,
    stock_root: Path,
) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    by_code = {item["code"]: item for item in watchlist_items}
    by_watch_name = {item["name"]: item for item in watchlist_items}
    for row in quick_rows:
        company = by_name.setdefault(
            row["company"],
            {
                "name": row["company"],
                "code": row["code"],
                "chainIds": [],
                "stageIds": [],
                "chains": [],
                "stages": [],
                "priority": row["priority"],
                "heat": row["heat"],
                "notes": [],
                "risks": [],
                "sourceRefs": [],
            },
        )
        chain_id = slug(row["chain"])
        stage_id = f"{chain_id}-{slug(row['stage'])}"
        append_unique(company["chainIds"], chain_id)
        append_unique(company["stageIds"], stage_id)
        append_unique(company["chains"], row["chain"])
        append_unique(company["stages"], row["stage"])
        append_unique(company["notes"], row["note"])
        company["priority"] = min_priority(company["priority"], row["priority"])
        company["heat"] = max(company["heat"], row["heat"], frequencies.get(row["company"], {}).get("count", 0))

    for name, company in by_name.items():
        freq = frequencies.get(name, {})
        company["dateRange"] = freq.get("dateRange", "")
        company["sourceRefs"].extend(freq.get("sourceRefs", []))
        item = by_code.get(company["code"]) or by_watch_name.get(name)
        if item:
            company["price"] = item["price"]
            company["priceDate"] = item["priceDate"]
            company["ownership"] = item["ownership"]
        else:
            company["price"] = "--"
            company["priceDate"] = "--"
            company["ownership"] = "未在自选/持仓"
        card_path = cards_dir / f"{sanitize_filename(name)}.md"
        if card_path.exists():
            card = extract_company_card(card_path)
            company["cardPath"] = str(card_path.relative_to(stock_root).as_posix())
            company["summary"] = card["summary"]
            company["risks"] = card["risks"]
            company["sourceRefs"].extend(card["sourceRefs"])
        else:
            company["summary"] = "待补：未找到公司卡或公司卡尚未沉淀。"
            company["cardPath"] = ""
        company["sourceRefs"] = dedupe_refs(company["sourceRefs"])
    return sorted(by_name.values(), key=lambda item: (priority_rank(item["priority"]), -item["heat"], item["name"]))


def build_industry_chains(quick_rows: list[dict[str, Any]], source_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chains: dict[str, dict[str, Any]] = {}
    for row in quick_rows:
        chain_id = slug(row["chain"])
        chain = chains.setdefault(
            chain_id,
            {"id": chain_id, "name": row["chain"], "bottleneckLevel": "待核验", "stages": [], "heatByMonth": {}},
        )
        stage_id = f"{chain_id}-{slug(row['stage'])}"
        stage = next((item for item in chain["stages"] if item["id"] == stage_id), None)
        if not stage:
            stage = {"id": stage_id, "chainId": chain_id, "name": row["stage"], "priority": row["priority"], "companies": []}
            chain["stages"].append(stage)
        stage["priority"] = min_priority(stage["priority"], row["priority"])
        stage["companies"].append({"name": row["company"], "code": row["code"], "priority": row["priority"], "heat": row["heat"]})

    for source in source_files:
        title = source["title"]
        text = f"{title} {' '.join(source['companies'])}"
        for chain in chains.values():
            score = 0
            if chain["name"] in text:
                score += 2
            for stage in chain["stages"]:
                if stage["name"] in text:
                    score += 1
                score += sum(1 for company in stage["companies"] if company["name"] in source["companies"])
            if score:
                month = source["month"]
                chain["heatByMonth"][month] = chain["heatByMonth"].get(month, 0) + score

    return sorted(chains.values(), key=lambda item: item["name"])


def build_watchlist(
    watchlist_items: list[dict[str, Any]],
    companies: list[dict[str, Any]],
    snapshots: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    by_code = {company["code"]: company for company in companies}
    by_name = {company["name"]: company for company in companies}
    result = []
    for item in watchlist_items:
        company = by_code.get(item["code"]) or by_name.get(item["name"])
        next_item = dict(item)
        if company:
            next_item["chainIds"] = company["chainIds"]
            next_item["chains"] = company["chains"]
            next_item["priority"] = company["priority"]
            next_item["heat"] = company["heat"]
        else:
            next_item["chainIds"] = []
            next_item["chains"] = ["未归类"]
            next_item["priority"] = "P3"
            next_item["heat"] = 0
        next_item["change5d"] = calculate_snapshot_change(item["code"], item["price"], item["priceDate"], snapshots, 5)
        next_item["change10d"] = calculate_snapshot_change(item["code"], item["price"], item["priceDate"], snapshots, 10)
        result.append(next_item)
    return sorted(result, key=lambda item: (item["chains"][0], priority_rank(item["priority"]), item["name"]))


def append_unique(items: list[Any], value: Any) -> None:
    if value and value not in items:
        items.append(value)


def dedupe_refs(refs: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for ref in refs:
        key = (ref.get("target"), ref.get("label"))
        if key not in seen:
            seen.add(key)
            result.append(ref)
    return result[:16]


def sanitize_filename(value: str) -> str:
    return value.replace("/", "-").replace("\\", "-").strip()


def priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)


def min_priority(left: str, right: str) -> str:
    return left if priority_rank(left) <= priority_rank(right) else right


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build stock web app cache from ClayMore wiki.")
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT)
    parser.add_argument("--out-dir", type=Path, default=APP_ROOT / "data" / "cache")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_cache(args.wiki_root, args.out_dir)
    print(f"cache built: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
