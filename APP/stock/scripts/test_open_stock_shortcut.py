import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "open-stock.ps1"
PACKAGE_JSON = ROOT / "stock" / "package.json"


def test_open_stock_shortcut_exists_at_app_root():
    assert SCRIPT.exists()


def test_open_stock_shortcut_reuses_running_server_before_starting_dev():
    content = SCRIPT.read_text(encoding="utf-8")

    port_check = content.find("Test-StockPort")
    dev_start = content.find("Start-StockDevServer")

    assert port_check != -1
    assert dev_start != -1
    assert port_check < dev_start


def test_open_stock_shortcut_refreshes_cache_and_opens_default_browser():
    content = SCRIPT.read_text(encoding="utf-8")

    assert "npm.cmd" in content
    assert "build:cache" in content
    assert "Start-Process $Url" in content


def test_stock_package_exposes_open_shortcut():
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    assert package["scripts"]["open"] == "powershell -ExecutionPolicy Bypass -File ../open-stock.ps1"


if __name__ == "__main__":
    tests = [
        test_open_stock_shortcut_exists_at_app_root,
        test_open_stock_shortcut_reuses_running_server_before_starting_dev,
        test_open_stock_shortcut_refreshes_cache_and_opens_default_browser,
        test_stock_package_exposes_open_shortcut,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} open-stock shortcut tests passed")
