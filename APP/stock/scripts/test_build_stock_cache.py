import unittest

from build_stock_cache import (
    DEFAULT_WIKI_ROOT,
    calculate_snapshot_change,
    clean_company_name,
    display_path,
    parse_frequency_rows,
    parse_markdown_table,
    parse_stock_quick_rows,
)


class MarkdownParsingTests(unittest.TestCase):
    def test_parse_markdown_table_returns_dict_rows(self):
        text = """
| 主线 | 环节 | 公司 |
|---|---|---|
| AI算力链 | 光模块 | <span style="color:#d6a100">新易盛</span> |
| 半导体 | 设备 | 北方华创 |
"""

        rows = parse_markdown_table(text)

        self.assertEqual(rows[0]["主线"], "AI算力链")
        self.assertEqual(rows[0]["环节"], "光模块")
        self.assertEqual(rows[1]["公司"], "北方华创")

    def test_clean_company_name_removes_highlight_span_and_alias_note(self):
        value = '<span style="color:#d6a100">*ST铖昌</span>（自选缓存名：<span style="color:#d6a100">铖昌科技</span>）'

        self.assertEqual(clean_company_name(value), "*ST铖昌")

    def test_parse_stock_quick_rows_normalizes_company_and_numbers(self):
        text = """
| 主线 | 环节 | 优先级 | 公司 | 代码 | 资料热度 | 备注 |
|---|---|---|---|---|---:|---|
| 光模块/CPO | 光模块龙头 | P0 | <span style="color:#d6a100">新易盛</span> | SZ300502 | 7 | 自选池内光模块核心标的 |
"""

        rows = parse_stock_quick_rows(text)

        self.assertEqual(rows[0]["chain"], "光模块/CPO")
        self.assertEqual(rows[0]["stage"], "光模块龙头")
        self.assertEqual(rows[0]["priority"], "P0")
        self.assertEqual(rows[0]["company"], "新易盛")
        self.assertEqual(rows[0]["code"], "SZ300502")
        self.assertEqual(rows[0]["heat"], 7)

    def test_parse_frequency_rows_extracts_count_and_source_refs(self):
        text = """
| 排名 | 公司名 | 出现次数 | 涉及资料数 | 资料日期范围 | 代表资料 |
|---:|---|---:|---:|---|---|
| 1 | 盛合晶微 | 22 | 7 | 2026（04-21 ---> 05-26） | [[主题资料总结/行业/半导体/2026-05-25 - 先进封装封测篇]]；[[主题资料总结/行业/半导体/2026-05-26 - 先进封装材料篇]] |
"""

        rows = parse_frequency_rows(text)

        self.assertEqual(rows["盛合晶微"]["count"], 22)
        self.assertEqual(rows["盛合晶微"]["dateRange"], "2026（04-21 ---> 05-26）")
        self.assertEqual(len(rows["盛合晶微"]["sourceRefs"]), 2)


class SnapshotChangeTests(unittest.TestCase):
    def test_calculate_snapshot_change_uses_nearest_prior_date(self):
        snapshots = {
            "20260520": {"SZ300502": 100.0},
            "20260526": {"SZ300502": 121.0},
            "20260601": {"SZ300502": 133.1},
        }

        result = calculate_snapshot_change("SZ300502", "133.1", "20260601", snapshots, 5)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["fromDate"], "20260526")
        self.assertAlmostEqual(result["percent"], 10.0, places=2)

    def test_calculate_snapshot_change_reports_missing_when_history_absent(self):
        snapshots = {"20260601": {"SZ300502": 133.1}}

        result = calculate_snapshot_change("SZ300502", "133.1", "20260601", snapshots, 10)

        self.assertEqual(result["status"], "本地快照不足")


class PathFormattingTests(unittest.TestCase):
    def test_display_path_uses_app_relative_path_for_default_wiki_root(self):
        self.assertEqual(display_path(DEFAULT_WIKI_ROOT), "../../ClayMore")


if __name__ == "__main__":
    unittest.main()
