from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import adata


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "ClayMore" / "Wiki" / "10-股票投资" / "02-股票研究流" / "基础数据"
OUT_CSV = OUT_DIR / "A股公司名称库.csv"
OUT_JSON = OUT_DIR / "A股公司名称库.json"
OUT_README = OUT_DIR / "README.md"


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def load_rows() -> list[dict[str, str]]:
    data = adata.stock.info.all_code()
    rows: list[dict[str, str]] = []
    for item in data.to_dict("records"):
        raw_code = normalize_text(item.get("stock_code"))
        market = normalize_text(item.get("exchange")).upper()
        name = normalize_text(item.get("short_name"))
        list_date = normalize_text(item.get("list_date"))
        if not raw_code or not market or not name:
            continue
        rows.append(
            {
                "code": f"{market}{raw_code}",
                "raw_code": raw_code,
                "market": market,
                "name": name,
                "fullname": "",
                "board": "",
                "source": "adata.stock.info.all_code",
                "updated": today(),
                "listed_date": list_date,
            }
        )
    rows.sort(key=lambda row: row["code"])
    return rows


def write_outputs(rows: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "code",
        "raw_code",
        "market",
        "name",
        "fullname",
        "board",
        "source",
        "updated",
        "listed_date",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    market_counts: dict[str, int] = {}
    for row in rows:
        market_counts[row["market"]] = market_counts.get(row["market"], 0) + 1
    counts_text = "、".join(f"{market} {count}" for market, count in sorted(market_counts.items()))
    OUT_README.write_text(
        "\n".join(
            [
                "# A股公司名称库",
                "",
                "本目录存放用于股票资料公司名校验的本地基础数据。",
                "",
                "- `A股公司名称库.csv`：主要供人工查看和表格处理。",
                "- `A股公司名称库.json`：主要供脚本读取。",
                "",
                "当前主来源：`adata.stock.info.all_code()`，覆盖沪深北代码、证券简称、交易所和上市日期。用途只限公司名/证券简称/代码/市场校验，不用于确认供应链关系、客户、订单、份额、业绩或投资结论。",
                "",
                "权威复核来源可使用：上交所股票列表、深交所 A 股列表、北交所股票列表/代码对照表、巨潮公司列表。",
                "",
                f"更新时间：{today()}",
                f"记录数：{len(rows)}",
                f"市场分布：{counts_text}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    rows = load_rows()
    write_outputs(rows)
    print(f"updated: {OUT_CSV}")
    print(f"updated: {OUT_JSON}")
    print(f"updated: {OUT_README}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
