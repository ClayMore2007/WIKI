from __future__ import annotations

import argparse
import json
import locale
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable


MARKET_MAP = {
    "17": "16",
    "20": "16",
    "33": "32",
    "36": "32",
    "151": "144",
    "177": "176",
    "UOFJ": "32",
}


@dataclass(frozen=True)
class NameEntry:
    name: str
    display_code: str


@dataclass(frozen=True)
class StockRow:
    code: str
    name: str
    market: str
    raw_code: str
    price: str
    date: str
    source: str
    export_time: str
    block_key: str = ""


@dataclass(frozen=True)
class Summary:
    kind: str
    records: int
    missing_names: int
    missing_price_or_date: int
    duplicate_codes: int
    added: int
    removed: int
    raw: Path
    target: Path
    log: Path


def read_text_guess(path: Path) -> str:
    encodings = []
    preferred = locale.getpreferredencoding(False)
    if preferred:
        encodings.append(preferred)
    encodings.extend(["gbk", "utf-8-sig", "utf-8"])

    seen = set()
    for encoding in encodings:
        if encoding.lower() in seen:
            continue
        seen.add(encoding.lower())
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_utf8(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def display_code(name_market: str, raw_code: str, alias: str) -> str:
    display_raw = alias if alias.isdigit() and len(alias) in (5, 6) else raw_code
    if name_market == "16":
        return f"SH{display_raw}"
    if name_market == "32":
        return f"SZ{display_raw}"
    if name_market == "176":
        return display_raw.zfill(5) if display_raw.isdigit() else display_raw
    return display_raw


def fallback_display_code(market: str, raw_code: str) -> str:
    if market in {"17", "20", "16"}:
        if raw_code == "1A0001":
            return "SH000001"
        return f"SH{raw_code}"
    if market in {"33", "36", "32"}:
        return f"SZ{raw_code}"
    if market == "177" and raw_code.startswith("HK") and raw_code[2:].isdigit():
        return raw_code[2:].zfill(5)
    return raw_code


def import_name_map(name_dir: Path) -> dict[tuple[str, str], NameEntry]:
    if not name_dir.exists():
        raise FileNotFoundError(f"名称映射目录不存在：{name_dir}")

    result: dict[tuple[str, str], NameEntry] = {}
    for path in name_dir.glob("stockname_*_0.txt"):
        stem = path.name.removeprefix("stockname_").removesuffix("_0.txt")
        name_market = stem
        for line in read_text_guess(path).splitlines():
            line = line.strip()
            if not line or line.startswith("[") or line.startswith("ConfigVer=") or "=" not in line:
                continue
            raw_code, right = line.split("=", 1)
            raw_code = raw_code.strip()
            right = right.strip()
            if "|" in right:
                name, alias_part = right.split("|", 1)
                alias = alias_part.split("@", 1)[0].strip()
            else:
                name = right
                alias = ""
            entry = NameEntry(
                name=name.strip(),
                display_code=display_code(name_market, raw_code, alias),
            )
            result[(name_market, raw_code)] = entry
            if alias.isdigit():
                result.setdefault((name_market, alias), entry)
    return result


def parse_self_rows(self_path: Path, name_map: dict[tuple[str, str], NameEntry], export_time: str) -> list[StockRow]:
    if not self_path.exists():
        raise FileNotFoundError(f"自选股源文件不存在：{self_path}")
    data = json.loads(self_path.read_text(encoding="utf-8-sig"))
    rows: list[StockRow] = []
    for item in data:
        raw_code = str(item.get("C", ""))
        market = str(item.get("M", ""))
        lookup_market = MARKET_MAP.get(market, market)
        entry = name_map.get((lookup_market, raw_code))
        if entry:
            name = entry.name
            code = raw_code if market == "UOFJ" else entry.display_code
        else:
            name = "--"
            code = fallback_display_code(market, raw_code)
        price = str(item.get("P") or "--")
        record_date = str(item.get("T") or "--")
        rows.append(
            StockRow(
                code=code,
                name=name,
                market=market,
                raw_code=raw_code,
                price=price,
                date=record_date,
                source=str(self_path),
                export_time=export_time,
            )
        )
    return rows


def price_map(rows: Iterable[StockRow]) -> dict[tuple[str, str], StockRow]:
    return {(row.market, row.raw_code): row for row in rows}


def parse_old_codes(path: Path, heading: str) -> list[str]:
    if not path.exists():
        return []
    codes: list[str] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == heading:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|"):
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if parts and parts[0] not in {"代码", "---"}:
                codes.append(parts[0])
    return codes


def validate_rows(rows: list[StockRow], kind: str) -> None:
    missing_names = [row for row in rows if row.name == "--"]
    bad_codes = [row for row in rows if row.code.startswith(("SH1A", "SZ1A", "SHHK", "SZHK"))]
    if missing_names or bad_codes:
        raise ValueError(f"{kind} 校验失败：名称缺失 {len(missing_names)}，异常代码 {len(bad_codes)}")


def changes(old_codes: list[str], rows: list[StockRow]) -> tuple[list[str], list[str]]:
    new_codes = [row.code for row in rows]
    added = [code for code in new_codes if code not in old_codes]
    removed = [code for code in old_codes if code not in new_codes]
    return added, removed


def duplicate_count(rows: list[StockRow]) -> int:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.code] = counts.get(row.code, 0) + 1
    return sum(1 for count in counts.values() if count > 1)


def table_lines(headers: list[str], rows: list[StockRow], render_row) -> list[str]:
    align = ["---:" if any(word in header for word in ("价格", "现价", "市场代码", "数量")) else "---" for header in headers]
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
        *[render_row(row) for row in rows],
    ]


def text_or_none(items: list[str]) -> str:
    return "、".join(items) if items else "无"


def write_self_files(wiki_root: Path, rows: list[StockRow], self_path: Path, name_dir: Path, run_date: str, compact_date: str, export_time: str) -> Summary:
    validate_rows(rows, "自选股")
    raw_rel = f"80-raw-原始资料/同花顺自选股/同花顺自选股_{compact_date}.md"
    target_rel = "Wiki/10-股票投资/02-股票研究流/我的自选.md"
    log_rel = f"00-log-整理日志/{run_date}-同花顺自选股更新.md"
    raw = wiki_root / Path(raw_rel)
    target = wiki_root / Path(target_rel)
    log = wiki_root / Path(log_rel)

    old_codes = parse_old_codes(target, "## 自选表")
    added, removed = changes(old_codes, rows)
    missing_price_or_date = [row for row in rows if row.price == "--" or row.date == "--"]
    dupes = duplicate_count(rows)

    raw_lines = [
        "---",
        "type: raw",
        f"created: {run_date}",
        "source_type: local-ths-self-stock-cache",
        "sources:",
        f"  - 本机同花顺自选股缓存：{self_path}",
        f"  - 本机同花顺名称表：{name_dir}\\stockname_*_0.txt",
        "confidence: medium",
        "---",
        "",
        f"# 同花顺自选股 - {run_date}",
        "",
        "来源为本机同花顺自选股缓存文件；价格和日期是本地记录值，可能不是实时行情。该清单仅用于个人观察和 Wiki 记录，不构成投资建议。",
        "",
        "## 导出信息",
        "",
        f"- 自选股源文件：{self_path}",
        f"- 名称映射目录：{name_dir}",
        f"- 导出时间：{export_time}",
        f"- 记录数：{len(rows)}",
        "- 名称缺失：0",
        f"- 价格或日期缺失：{len(missing_price_or_date)}",
        "",
        "## 自选股表",
        "",
        *table_lines(
            ["代码", "名称", "市场代码", "价格", "日期", "来源文件", "导出时间"],
            rows,
            lambda row: f"| {row.code} | {row.name} | {row.market} | {row.price} | {row.date} | {row.source} | {row.export_time} |",
        ),
    ]

    target_lines = [
        "---",
        "type: stock-list",
        f"updated: {run_date}",
        "sources:",
        f"  - [[80-raw-原始资料/同花顺自选股/同花顺自选股_{compact_date}]]",
        "confidence: medium",
        "---",
        "",
        "# 我的自选",
        "",
        f"本页由 raw 数据源 {raw_rel} 更新。自选池用于跟踪候选标的和后续研究问题，不构成投资建议。价格和日期来自本机同花顺缓存，可能不是实时行情。",
        "",
        "## 更新信息",
        "",
        f"- 数据源：{raw_rel}",
        "- 解析方式：同花顺本地 SelfStockInfo.json + stockname_*_0.txt 名称映射。",
        f"- 更新日期：{run_date}",
        "- 更新规则：以后同花顺本地自选缓存变化后，重新生成 raw Markdown 并刷新本页表格。",
        "",
        "## 自选表",
        "",
        *table_lines(
            ["代码", "名称", "现价", "本地记录日期", "市场代码", "备注"],
            rows,
            lambda row: f"| {row.code} | {row.name} | {row.price} | {row.date} | {row.market} |  |",
        ),
        "",
        "## 待补充信息",
        "",
        "| 项 | 状态 |",
        "|---|---|",
        "| 行业分类 | 同花顺缓存源未提供，本次不补写 |",
        "| 估值/市值/财务指标 | 同花顺缓存源未提供，本次不补写 |",
        "| 研究优先级 | 待人工判断 |",
        "",
        "> 本次同花顺缓存源不包含行业、估值和总金额字段；未从其他行情源补写，避免把缺源数据写成确定结论。",
    ]

    log_lines = [
        "---",
        "type: log",
        f"created: {run_date}",
        "sources:",
        f"  - [[80-raw-原始资料/同花顺自选股/同花顺自选股_{compact_date}]]",
        "  - [[Wiki/10-股票投资/02-股票研究流/我的自选]]",
        "---",
        "",
        f"# {run_date} 同花顺自选股更新",
        "",
        "## 来源",
        "",
        f"- 自选股源文件：{self_path}",
        f"- 名称映射目录：{name_dir}",
        f"- 导出时间：{export_time}",
        "",
        "## 结果",
        "",
        f"- 记录数：{len(rows)}",
        "- 名称缺失：0",
        f"- 价格或日期缺失：{len(missing_price_or_date)}",
        f"- 重复代码：{dupes}",
        f"- 新增：{len(added)}；{text_or_none(added)}",
        f"- 移除：{len(removed)}；{text_or_none(removed)}",
        f"- 导出 raw Markdown：[[80-raw-原始资料/同花顺自选股/同花顺自选股_{compact_date}]]",
        "- 更新目标页：[[Wiki/10-股票投资/02-股票研究流/我的自选]]",
        "",
        "## 风险提示",
        "",
        "- 来源为本机同花顺自选股缓存文件；价格和日期是本地记录值，可能不是实时行情。",
        "- 本次未读取交易记录、资金流水、账号、密码、券商登录、银行卡等高敏信息。",
        "- 该清单仅用于个人观察和 Wiki 记录，不构成投资建议。",
    ]

    write_utf8(raw, raw_lines)
    write_utf8(target, target_lines)
    write_utf8(log, log_lines)
    return Summary("self", len(rows), 0, len(missing_price_or_date), dupes, len(added), len(removed), raw, target, log)


def parse_holding_rows(stockblock_path: Path, block_key: str, name_map: dict[tuple[str, str], NameEntry], prices: dict[tuple[str, str], StockRow], export_time: str) -> list[StockRow]:
    if not stockblock_path.exists():
        raise FileNotFoundError(f"用户板块内容不存在：{stockblock_path}")
    block_line = None
    for line in read_text_guess(stockblock_path).splitlines():
        if line.startswith(f"{block_key}="):
            block_line = line
            break
    if block_line is None:
        raise ValueError(f"未找到持仓板块 key：{block_key}")

    rows: list[StockRow] = []
    for entry in block_line.split("=", 1)[1].split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        market, raw_code = entry.split(":", 1)
        lookup_market = MARKET_MAP.get(market, market)
        name_entry = name_map.get((lookup_market, raw_code))
        if name_entry:
            name = name_entry.name
            code = name_entry.display_code
        else:
            name = "--"
            code = fallback_display_code(market, raw_code)
        price_entry = prices.get((market, raw_code))
        price = price_entry.price if price_entry and price_entry.price else "--"
        record_date = price_entry.date if price_entry and price_entry.date else "--"
        rows.append(
            StockRow(
                code=code,
                name=name,
                market=market,
                raw_code=raw_code,
                price=price,
                date=record_date,
                source=str(stockblock_path),
                export_time=export_time,
                block_key=block_key,
            )
        )
    return rows


def write_holding_files(
    wiki_root: Path,
    rows: list[StockRow],
    block_name_path: Path,
    stockblock_path: Path,
    self_path: Path,
    name_dir: Path,
    block_key: str,
    run_date: str,
    compact_date: str,
    export_time: str,
) -> Summary:
    validate_rows(rows, "持仓")
    raw_rel = f"80-raw-原始资料/同花顺持仓板块/同花顺我的持仓_{compact_date}.md"
    target_rel = "Wiki/10-股票投资/02-股票研究流/我的持仓.md"
    log_rel = f"00-log-整理日志/{run_date}-同花顺我的持仓板块更新.md"
    raw = wiki_root / Path(raw_rel)
    target = wiki_root / Path(target_rel)
    log = wiki_root / Path(log_rel)

    old_codes = parse_old_codes(target, "## 持仓表")
    added, removed = changes(old_codes, rows)
    missing_price_or_date = [row for row in rows if row.price == "--" or row.date == "--"]
    dupes = duplicate_count(rows)

    raw_lines = [
        "---",
        "type: raw",
        f"created: {run_date}",
        "source_type: local-ths-stock-block",
        "sources:",
        f"  - 本机同花顺板块名称索引：{block_name_path}",
        f"  - 本机同花顺用户板块内容：{stockblock_path}",
        f"  - 本机同花顺自选股缓存：{self_path}",
        f"  - 本机同花顺名称表：{name_dir}\\stockname_*_0.txt",
        "confidence: medium",
        "---",
        "",
        f"# 同花顺我的持仓板块 - {run_date}",
        "",
        "来源为本机同花顺“我的板块”中的 我的持仓 板块；该板块只提供股票代码清单，不等同于券商真实持仓。价格和日期来自本地同花顺缓存，可能不是实时行情。该清单仅用于个人观察和 Wiki 记录，不构成投资建议。",
        "",
        "## 导出信息",
        "",
        f"- 板块名来源：{block_name_path}",
        f"- 板块成分来源：{stockblock_path}",
        f"- 板块 key：{block_key}",
        f"- 名称映射目录：{name_dir}",
        f"- 价格日期缓存：{self_path}",
        f"- 导出时间：{export_time}",
        f"- 记录数：{len(rows)}",
        "- 名称缺失：0",
        f"- 价格或日期缺失：{len(missing_price_or_date)}",
        "",
        "## 持仓板块表",
        "",
        *table_lines(
            ["代码", "名称", "市场代码", "本地记录价格", "本地记录日期", "板块 key", "来源文件", "导出时间"],
            rows,
            lambda row: f"| {row.code} | {row.name} | {row.market} | {row.price} | {row.date} | {row.block_key} | {row.source} | {row.export_time} |",
        ),
    ]

    target_lines = [
        "---",
        "type: stock-list",
        f"updated: {run_date}",
        "sources:",
        f"  - [[80-raw-原始资料/同花顺持仓板块/同花顺我的持仓_{compact_date}]]",
        "confidence: medium",
        "---",
        "",
        "# 我的持仓",
        "",
        f"本页由 raw 数据源 {raw_rel} 更新。来源是本机同花顺“我的板块”中的 我的持仓 板块，不是券商交易持仓；仅作个人跟踪和复盘入口，不构成投资建议。",
        "",
        "## 更新信息",
        "",
        f"- 数据源：{raw_rel}",
        f"- 解析方式：读取同花顺 stockblock.ini 中 {block_key}=我的持仓 的板块成分，并用本地名称表补齐名称。",
        f"- 更新日期：{run_date}",
        "- 更新规则：以后同花顺“我的持仓”板块变化后，重新生成 raw Markdown 并刷新本页表格。",
        "",
        "## 持仓表",
        "",
        *table_lines(
            ["代码", "名称", "本地记录价格", "本地记录日期", "市场代码", "备注"],
            rows,
            lambda row: f"| {row.code} | {row.name} | {row.price} | {row.date} | {row.market} |  |",
        ),
        "",
        "## 行业分类",
        "",
        "| 分类 | 数量 | 标的 |",
        "|---|---:|---|",
        f"| 未标注 | {len(rows)} | {'、'.join(row.code for row in rows)} |",
        "",
        "> 本次来源是同花顺自定义板块，仅提供代码列表；行业、估值、持仓数量、成本、市值、盈亏、总金额等字段未从其他来源补写。",
    ]

    log_lines = [
        "---",
        "type: log",
        f"created: {run_date}",
        "sources:",
        f"  - [[80-raw-原始资料/同花顺持仓板块/同花顺我的持仓_{compact_date}]]",
        "  - [[Wiki/10-股票投资/02-股票研究流/我的持仓]]",
        "---",
        "",
        f"# {run_date} 同花顺我的持仓板块更新",
        "",
        "## 来源",
        "",
        f"- 板块名来源：{block_name_path}",
        f"- 板块成分来源：{stockblock_path}",
        f"- 板块 key：{block_key}",
        f"- 名称映射目录：{name_dir}",
        f"- 价格日期缓存：{self_path}",
        f"- 导出时间：{export_time}",
        "",
        "## 结果",
        "",
        f"- 记录数：{len(rows)}",
        "- 名称缺失：0",
        f"- 价格或日期缺失：{len(missing_price_or_date)}",
        f"- 重复代码：{dupes}",
        f"- 新增：{len(added)}；{text_or_none(added)}",
        f"- 移除：{len(removed)}；{text_or_none(removed)}",
        f"- 导出 raw Markdown：[[80-raw-原始资料/同花顺持仓板块/同花顺我的持仓_{compact_date}]]",
        "- 更新目标页：[[Wiki/10-股票投资/02-股票研究流/我的持仓]]",
        "",
        "## 风险提示",
        "",
        "- 来源是同花顺“我的板块”中的自定义板块，不等同于券商真实交易持仓。",
        "- 本次未读取交易记录、资金流水、账号、密码、券商登录、银行卡等高敏信息。",
        "- 价格和日期来自本地同花顺缓存，可能不是实时行情。",
        "- 该清单仅用于个人观察和 Wiki 记录，不构成投资建议。",
    ]

    write_utf8(raw, raw_lines)
    write_utf8(target, target_lines)
    write_utf8(log, log_lines)
    return Summary("holdings", len(rows), 0, len(missing_price_or_date), dupes, len(added), len(removed), raw, target, log)


def write_stock_info_summary(
    wiki_root: Path,
    self_rows: list[StockRow],
    holding_rows: list[StockRow],
    run_date: str,
    compact_date: str,
) -> Summary:
    target_rel = "Wiki/10-股票投资/02-股票研究流/我的股票信息.md"
    target = wiki_root / Path(target_rel)
    holding_codes = {row.code for row in holding_rows}
    self_codes = {row.code for row in self_rows}
    holding_only = [row for row in holding_rows if row.code not in self_codes]
    self_only = [row for row in self_rows if row.code not in holding_codes]
    missing_price_or_date = [row for row in [*holding_rows, *self_rows] if row.price == "--" or row.date == "--"]
    dupes = duplicate_count(holding_rows) + duplicate_count(self_rows)

    def ownership(row: StockRow) -> str:
        if row.code in holding_codes and row.code in self_codes:
            return "持仓 + 自选"
        if row.code in holding_codes:
            return "持仓"
        return "自选"

    def missing_note(row: StockRow) -> str:
        return "价格或日期缺失" if row.price == "--" or row.date == "--" else ""

    target_lines = [
        "---",
        "status: active",
        f"updated: {run_date}",
        "confidence: medium",
        "sources:",
        "  - \"[[Wiki/10-股票投资/02-股票研究流/我的持仓]]\"",
        "  - \"[[Wiki/10-股票投资/02-股票研究流/我的自选]]\"",
        f"  - \"[[80-raw-原始资料/同花顺自选股/同花顺自选股_{compact_date}]]\"",
        f"  - \"[[80-raw-原始资料/同花顺持仓板块/同花顺我的持仓_{compact_date}]]\"",
        "---",
        "",
        "# 我的股票信息",
        "",
        "本页把同花顺缓存生成的“我的持仓”和“我的自选”整理成便于查看的 Markdown 表格。来源为本机同花顺缓存和自定义板块；价格和日期是本地记录值，可能不是实时行情。该清单仅用于个人观察和 Wiki 记录，不构成投资建议。",
        "",
        "## 更新摘要",
        "",
        "| 项目 | 数量 | 说明 |",
        "|---|---:|---|",
        f"| 我的持仓 | {len(holding_rows)} | 来自同花顺“我的持仓”自定义板块，不等同于券商真实持仓 |",
        f"| 我的自选 | {len(self_rows)} | 来自同花顺本地自选缓存 |",
        f"| 仅自选未持仓 | {len(self_only)} | 自选表中未出现在“我的持仓”板块的标的 |",
        f"| 持仓未在自选 | {len(holding_only)} | 用于检查自选池与持仓板块是否脱节 |",
        f"| 价格或日期缺失 | {len(missing_price_or_date)} | 当前为指数或缓存未提供价格/日期的记录 |",
        "",
        "## 我的持仓",
        "",
        *table_lines(
            ["代码", "名称", "本地记录价格", "本地记录日期", "市场代码", "归属", "备注"],
            holding_rows,
            lambda row: f"| {row.code} | {row.name} | {row.price} | {row.date} | {row.market} | {ownership(row)} | {missing_note(row)} |",
        ),
        "",
        "## 自选股",
        "",
        *table_lines(
            ["代码", "名称", "现价", "本地记录日期", "市场代码", "归属", "备注"],
            self_rows,
            lambda row: f"| {row.code} | {row.name} | {row.price} | {row.date} | {row.market} | {ownership(row)} | {missing_note(row)} |",
        ),
        "",
        "## 待补充信息",
        "",
        "| 项 | 状态 |",
        "|---|---|",
        "| 行业分类 | 同花顺缓存源未提供，本页不补写 |",
        "| 估值/市值/财务指标 | 同花顺缓存源未提供，本页不补写 |",
        "| 真实仓位/成本/盈亏 | 未读取券商交易记录，本页不记录 |",
        "| 研究优先级 | 待人工判断，可后续从分析页补充 |",
        "",
        "## 相关页面",
        "",
        "- [[Wiki/10-股票投资/02-股票研究流/我的持仓]]",
        "- [[Wiki/10-股票投资/02-股票研究流/我的自选]]",
        "- [[Wiki/10-股票投资/02-股票研究流/我的持仓分析]]",
    ]

    write_utf8(target, target_lines)
    return Summary("stock_info", len(holding_codes | self_codes), 0, len(missing_price_or_date), dupes, 0, 0, target, target, target)


def default_export_time() -> str:
    now = datetime.now(timezone(timedelta(hours=8)))
    return now.strftime("%Y-%m-%d %H:%M:%S %z")[:-2] + ":" + now.strftime("%z")[-2:]


def parse_args() -> argparse.Namespace:
    workspace_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Update ClayMore stock wiki pages from local 同花顺 files.")
    parser.add_argument("--only", choices=["all", "self", "holdings"], default="all", help="which stock list to update")
    parser.add_argument("--wiki-root", type=Path, default=workspace_root / "ClayMore", help="ClayMore wiki root")
    parser.add_argument("--ths-root", type=Path, default=Path(r"C:\同花顺软件\同花顺"), help="同花顺 installation data root")
    parser.add_argument("--profile-id", default="mx_4mx395jk7", help="同花顺 user profile directory")
    parser.add_argument("--block-key", default="CAF9", help="同花顺 我的持仓 block key")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="output date, YYYY-MM-DD")
    parser.add_argument("--export-time", default=default_export_time(), help="export timestamp used in generated notes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    compact_date = args.date.replace("-", "")
    profile_dir = args.ths_root / args.profile_id
    self_path = profile_dir / "SelfStockInfo.json"
    stockblock_path = profile_dir / "stockblock.ini"
    name_dir = args.ths_root / "stockname"
    block_name_path = args.ths_root / "system" / "同花顺方案" / "StockBlock.ini"

    name_map = import_name_map(name_dir)
    self_rows = parse_self_rows(self_path, name_map, args.export_time)
    summaries: list[Summary] = []

    if args.only in {"all", "self"}:
        summaries.append(write_self_files(args.wiki_root, self_rows, self_path, name_dir, args.date, compact_date, args.export_time))

    holding_rows: list[StockRow] = []
    if args.only in {"all", "holdings"}:
        holding_rows = parse_holding_rows(stockblock_path, args.block_key, name_map, price_map(self_rows), args.export_time)
        summaries.append(
            write_holding_files(
                args.wiki_root,
                holding_rows,
                block_name_path,
                stockblock_path,
                self_path,
                name_dir,
                args.block_key,
                args.date,
                compact_date,
                args.export_time,
            )
        )

    if args.only == "all":
        summaries.append(write_stock_info_summary(args.wiki_root, self_rows, holding_rows, args.date, compact_date))

    for summary in summaries:
        print(
            f"{summary.kind}: records={summary.records}, missing_names={summary.missing_names}, "
            f"missing_price_or_date={summary.missing_price_or_date}, duplicates={summary.duplicate_codes}, "
            f"added={summary.added}, removed={summary.removed}, target={summary.target}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
