import json
import locale
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("update_ths_stocks.py")


class UpdateThsStocksTest(unittest.TestCase):
    def assert_markdown_table_has_no_blank_rows(self, text: str, heading: str) -> None:
        lines = text.splitlines()
        start = lines.index(heading)
        table_lines = []
        for line in lines[start + 1 :]:
            if table_lines and not line.startswith("|"):
                break
            if line.startswith("|") or table_lines:
                table_lines.append(line)

        self.assertGreaterEqual(len(table_lines), 3, f"missing table under {heading}")
        self.assertNotIn("", table_lines, f"blank line breaks Markdown table under {heading}")

    def test_updates_self_and_holdings_from_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ths-stock-script-test-") as temp:
            root = Path(temp)
            wiki_root = root / "ClayMore"
            ths_root = root / "同花顺"
            profile_id = "mx_test"

            research_dir = wiki_root / "Wiki" / "10-股票投资" / "02-股票研究流"
            research_dir.mkdir(parents=True)
            (research_dir / "我的自选.md").write_text(
                "\n".join(
                    [
                        "# 我的自选",
                        "",
                        "## 自选表",
                        "",
                        "| 代码 | 名称 | 现价 | 本地记录日期 | 市场代码 | 备注 |",
                        "|---|---|---:|---|---:|---|",
                        "| SH600089 | 特变电工 | 25.00 | 20260512 | 17 |  |",
                    ]
                ),
                encoding="utf-8",
            )
            (research_dir / "我的持仓.md").write_text(
                "\n".join(
                    [
                        "# 我的持仓",
                        "",
                        "## 持仓表",
                        "",
                        "| 代码 | 名称 | 本地记录价格 | 本地记录日期 | 市场代码 | 备注 |",
                        "|---|---|---:|---|---:|---|",
                        "| SH600089 | 特变电工 | 25.00 | 20260512 | 17 |  |",
                    ]
                ),
                encoding="utf-8",
            )

            stockname_dir = ths_root / "stockname"
            stockname_dir.mkdir(parents=True)
            (stockname_dir / "stockname_16_0.txt").write_text(
                "\n".join(
                    [
                        "[name_16_16]",
                        "ConfigVer=fixture",
                        "1A0001=上证指数|000001@s",
                        "600089=特变电工|特变电工@f",
                    ]
                ),
                encoding="gbk",
            )
            (stockname_dir / "stockname_32_0.txt").write_text(
                "\n".join(
                    [
                        "[name_32_32]",
                        "ConfigVer=fixture",
                        "JSH923=半导体C|008888@s",
                        "JSJ033=芯片C|017470@s",
                        "000001=平安银行|平安银行@f",
                        "159665=半导体ETF|半导体ETF@f",
                    ]
                ),
                encoding="gbk",
            )
            (stockname_dir / "stockname_144_0.txt").write_text(
                "\n".join(
                    [
                        "[name_144_144]",
                        "ConfigVer=fixture",
                        "920438=戈碧迦|戈碧迦@f",
                    ]
                ),
                encoding="gbk",
            )

            (ths_root / "system" / "同花顺方案").mkdir(parents=True)
            (ths_root / "system" / "同花顺方案" / "StockBlock.ini").write_text(
                "[BLOCK_NAME_MAP_TABLE]\nCAF9=我的持仓\n",
                encoding="gbk",
            )
            profile_dir = ths_root / profile_id
            profile_dir.mkdir(parents=True)
            (profile_dir / "stockblock.ini").write_text(
                "[BLOCK_STOCK_CONTEXT]\nCAF9=17:600089,33:000001,\n",
                encoding="gbk",
            )
            (profile_dir / "SelfStockInfo.json").write_text(
                json.dumps(
                    [
                        {"C": "600089", "M": "17", "P": "26.96", "T": "20260513"},
                        {"C": "000001", "M": "33", "P": "10.10", "T": "20260513"},
                        {"C": "1A0001", "M": "16", "P": "", "T": ""},
                        {"C": "008888", "M": "UOFJ", "P": "", "T": "20260513"},
                        {"C": "017470", "M": "UOFJ", "P": "", "T": "20260513"},
                        {"C": "159665", "M": "UOFJ", "P": "", "T": "20260513"},
                        {"C": "920438", "M": "151", "P": "74.51", "T": "20260528"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--wiki-root",
                    str(wiki_root),
                    "--ths-root",
                    str(ths_root),
                    "--profile-id",
                    profile_id,
                    "--date",
                    "2026-05-13",
                    "--export-time",
                    "2026-05-13 09:30:00 +08:00",
                ],
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            self_raw = wiki_root / "80-raw-原始资料" / "同花顺自选股" / "同花顺自选股_20260513.md"
            hold_raw = wiki_root / "80-raw-原始资料" / "同花顺持仓板块" / "同花顺我的持仓_20260513.md"
            self_page = research_dir / "我的自选.md"
            hold_page = research_dir / "我的持仓.md"
            info_page = research_dir / "我的股票信息.md"
            self_log = wiki_root / "00-log-整理日志" / "2026-05-13-同花顺自选股更新.md"
            hold_log = wiki_root / "00-log-整理日志" / "2026-05-13-同花顺我的持仓板块更新.md"

            for path in [self_raw, hold_raw, self_page, hold_page, info_page, self_log, hold_log]:
                self.assertTrue(path.exists(), f"missing {path}")

            self_text = self_page.read_text(encoding="utf-8")
            hold_text = hold_page.read_text(encoding="utf-8")
            info_text = info_page.read_text(encoding="utf-8")
            log_text = self_log.read_text(encoding="utf-8") + hold_log.read_text(encoding="utf-8")

            self.assertIn("| SH600089 | 特变电工 | 26.96 | 20260513 | 17 |", self_text)
            self.assertIn("| SZ000001 | 平安银行 | 10.10 | 20260513 | 33 |", self_text)
            self.assertIn("| SH000001 | 上证指数 | -- | -- | 16 |", self_text)
            self.assertIn("| 008888 | 半导体C | -- | 20260513 | UOFJ |", self_text)
            self.assertIn("| 017470 | 芯片C | -- | 20260513 | UOFJ |", self_text)
            self.assertIn("| 159665 | 半导体ETF | -- | 20260513 | UOFJ |", self_text)
            self.assertIn("| 920438 | 戈碧迦 | 74.51 | 20260528 | 151 |", self_text)
            self.assertIn("| SH600089 | 特变电工 | 26.96 | 20260513 | 17 |", hold_text)
            self.assertIn("| SZ000001 | 平安银行 | 10.10 | 20260513 | 33 |", hold_text)
            self.assertIn("| 我的持仓 | 2 |", info_text)
            self.assertIn("| 我的自选 | 7 |", info_text)
            self.assertIn("| 仅自选未持仓 | 5 |", info_text)
            self.assertIn("| 持仓未在自选 | 0 |", info_text)
            self.assertIn("| 价格或日期缺失 | 4 |", info_text)
            self.assertIn("| SH000001 | 上证指数 | -- | -- | 16 | 自选 | 价格或日期缺失 |", info_text)
            self.assertIn("| 008888 | 半导体C | -- | 20260513 | UOFJ | 自选 | 价格或日期缺失 |", info_text)
            self.assert_markdown_table_has_no_blank_rows(self_text, "## 自选表")
            self.assert_markdown_table_has_no_blank_rows(hold_text, "## 持仓表")
            self.assert_markdown_table_has_no_blank_rows(info_text, "## 我的持仓")
            self.assert_markdown_table_has_no_blank_rows(info_text, "## 自选股")
            self.assertNotRegex(self_text + hold_text + log_text, r"\$(selfPath|nameDir|blockKey|stockBlockPath|blockNamePath)")
            self.assertNotRegex(self_text + hold_text, r"SH1A0001|SZ1A0001")
            self.assertIn("记录数：7", log_text)
            self.assertIn("记录数：2", log_text)
            self.assertIn("不构成投资建议", log_text)


if __name__ == "__main__":
    unittest.main()
