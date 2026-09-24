import sys
import tempfile
import unittest
from pathlib import Path

from figma_backup.browser import chromium_ready


def complete_layout(browser_dir: Path) -> None:
    if sys.platform == 'win32':
        binary = browser_dir / 'chrome-win64' / 'chrome.exe'
    else:
        binary = browser_dir / 'chrome-mac-arm64' / 'Google Chrome for Testing.app'
    binary.parent.mkdir(parents=True)
    binary.write_text('', encoding='utf-8')


class ChromiumReadyTests(unittest.TestCase):
    def make_cache(self, marker=False, binary=False):
        directory = Path(tempfile.mkdtemp())
        browser_dir = directory / 'chromium-1243'
        browser_dir.mkdir()
        if marker:
            (browser_dir / 'INSTALLATION_COMPLETE').write_text('', encoding='utf-8')
        if binary:
            complete_layout(browser_dir)
        return directory

    def test_missing_cache_dir_is_not_ready(self):
        self.assertFalse(chromium_ready(Path(tempfile.mkdtemp()) / 'absent'))

    def test_partial_install_without_marker_is_not_ready(self):
        self.assertFalse(chromium_ready(self.make_cache(binary=True)))

    def test_marker_without_binary_is_not_ready(self):
        self.assertFalse(chromium_ready(self.make_cache(marker=True)))

    def test_complete_install_is_ready(self):
        self.assertTrue(chromium_ready(self.make_cache(marker=True, binary=True)))


if __name__ == '__main__':
    unittest.main()
