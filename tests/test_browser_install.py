import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

from figma_backup import browser as browser_module
from figma_backup.browser import Browser, chromium_ready
from figma_backup.core import FigmaError


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


class FallbackSourceTests(unittest.TestCase):
    def test_ordering_puts_live_hosts_first(self):
        probes = {
            'https://cdn.playwright.dev': False,
            'https://registry.npmmirror.com/-/binary/playwright': True,
            'https://cdn.npmmirror.com/binaries/playwright': True,
        }
        with patch.object(Browser, '_chromium_archive_path', return_value='builds/cft/x.zip'), \
             patch.object(Browser, '_probe_host', side_effect=lambda host, _: probes[host]):
            order = [label for _, label in Browser._ordered_hosts()]
        self.assertEqual(order, ['npmmirror', 'npmmirror-cdn', 'playwright.dev'])

    def test_ordering_without_archive_keeps_default(self):
        with patch.object(Browser, '_chromium_archive_path', return_value=None):
            order = [label for _, label in Browser._ordered_hosts()]
        self.assertEqual(order, ['playwright.dev', 'npmmirror', 'npmmirror-cdn'])

    def test_install_falls_back_to_next_source(self):
        pairs = [('https://a', 'a'), ('https://b', 'b')]
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs.get('env', {}).get('PLAYWRIGHT_DOWNLOAD_HOST'))
            if len(calls) == 1:
                raise CalledProcessError(1, cmd, stderr='Error: Download failure, code=1')

        with patch.object(Browser, '_ordered_hosts', return_value=pairs), \
             patch.object(browser_module.subprocess, 'run', side_effect=fake_run):
            Browser._install_chromium()
        self.assertEqual(calls, ['https://a', 'https://b'])

    def test_install_aggregates_all_failures(self):
        pairs = [('https://a', 'a'), ('https://b', 'b')]

        def fake_run(cmd, **kwargs):
            raise CalledProcessError(1, cmd, stderr='Error: Download failure, code=1')

        with patch.object(Browser, '_ordered_hosts', return_value=pairs), \
             patch.object(browser_module.subprocess, 'run', side_effect=fake_run):
            with self.assertRaises(FigmaError) as ctx:
                Browser._install_chromium()
        self.assertIn('a: Error: Download failure, code=1', str(ctx.exception))
        self.assertIn('b: Error: Download failure, code=1', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
