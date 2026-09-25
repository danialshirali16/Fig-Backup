import platform
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

    def test_cft_archive_layout_matches_playwright_expectations(self):
        if sys.platform == 'win32':
            expected = {
                'chromium': ('builds/cft/153.0.8010.12/win64/chrome-win64.zip', 'chrome-win64'),
                'chromium-headless-shell': ('builds/cft/153.0.8010.12/win64/chrome-headless-shell-win64.zip',
                                            'chrome-headless-shell-win64'),
            }
        elif sys.platform == 'darwin':
            arch = 'mac-arm64' if platform.machine() == 'arm64' else 'mac-x64'
            expected = {
                'chromium': (f'builds/cft/153.0.8010.12/{arch}/chrome-{arch}.zip', f'chrome-{arch}'),
                'chromium-headless-shell': (f'builds/cft/153.0.8010.12/{arch}/chrome-headless-shell-{arch}.zip',
                                            f'chrome-headless-shell-{arch}'),
            }
        else:
            expected = {
                'chromium': ('builds/cft/153.0.8010.12/linux64/chrome-linux64.zip', 'chrome-linux64'),
                'chromium-headless-shell': ('builds/cft/153.0.8010.12/linux64/chrome-headless-shell-linux64.zip',
                                            'chrome-headless-shell-linux64'),
            }
        for name, wanted in expected.items():
            self.assertEqual(Browser._cft_archive(name, '153.0.8010.12'), wanted)

    def test_install_tries_next_host_when_download_fails(self):
        calls = []
        def fake_ensure(host, name):
            calls.append((host, name))
            if host == 'https://a':
                raise RuntimeError('download stalled')
        with patch.object(Browser, '_ordered_hosts',
                          return_value=[('https://a', 'a'), ('https://b', 'b')]), \
             patch.object(Browser, '_ensure_browser', side_effect=fake_ensure):
            Browser._install_chromium()
        self.assertEqual(calls, [('https://a', 'chromium'),
                                 ('https://b', 'chromium'),
                                 ('https://b', 'chromium-headless-shell')])

    def test_install_aggregates_all_failures(self):
        def fake_run(cmd, **kwargs):
            raise CalledProcessError(1, cmd, stderr='Error: Download failure, code=1')

        with patch.object(Browser, '_ordered_hosts',
                          return_value=[('https://a', 'a'), ('https://b', 'b')]), \
             patch.object(Browser, '_ensure_browser',
                          side_effect=RuntimeError('download stalled')), \
             patch.object(browser_module.subprocess, 'run', side_effect=fake_run):
            with self.assertRaises(FigmaError) as ctx:
                Browser._install_chromium()
        message = str(ctx.exception)
        self.assertIn('a: download stalled', message)
        self.assertIn('b: download stalled', message)
        self.assertIn('playwright-installer: Error: Download failure, code=1', message)

    def test_install_cli_last_resort_succeeds(self):
        with patch.object(Browser, '_ordered_hosts', return_value=[]), \
             patch.object(browser_module.subprocess, 'run'):
            Browser._install_chromium()


if __name__ == '__main__':
    unittest.main()
