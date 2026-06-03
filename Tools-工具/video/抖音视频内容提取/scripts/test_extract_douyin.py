from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("extract_douyin.py")
spec = importlib.util.spec_from_file_location("extract_douyin", SCRIPT)
extract_douyin = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["extract_douyin"] = extract_douyin
spec.loader.exec_module(extract_douyin)


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._body = body
        self._offset = 0
        self.headers = headers

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body) - self._offset
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class DownloadWithResumeTests(unittest.TestCase):
    def test_rejects_truncated_download_when_content_length_is_known(self) -> None:
        response = FakeResponse(b"abc", {"Content-Length": "10"})

        with tempfile.TemporaryDirectory() as tmp, patch.object(extract_douyin, "urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Incomplete download"):
                extract_douyin.download_with_resume("https://example.test/video.mp4", Path(tmp) / "video.mp4")


if __name__ == "__main__":
    unittest.main()
