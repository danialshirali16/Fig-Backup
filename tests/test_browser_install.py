import io
import json
import platform
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from subprocess import CalledProcessError
from types import SimpleNamespace
from unittest.mock import patch

from figma_backup import browser as browser_module
from figma_backup.browser import Browser, chromium_ready
from figma_backup.core import FigmaError


def binary_relative(name: str) -> Path:
    if sys.platform == 'win32':
        return Path('chrome-headless-shell-win64/chrome-headless-shell.exe' if name.endswith('headless-shell') else 'chrome-win64/chrome.exe')
    if sys.platform == 'darwin':
        arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
        return Path(f'chrome-headless-shell-mac-{arch}/chrome-headless-shell' if name.endswith('headless-shell') else f'chrome-mac-{arch}/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')
    return Path('chrome-headless-shell-linux64/chrome-headless-shell' if name.endswith('headless-shell') else 'chrome-linux64/chrome')


def complete_layout(browser_dir: Path, name: str = 'chromium') -> None:
    binary = browser_dir / binary_relative(name)
    binary.parent.mkdir(parents=True)
    binary.write_text('', encoding='utf-8')


class ChromiumReadyTests(unittest.TestCase):
    def make_cache(self, marker=False, binary=False, shell=True):
        directory = Path(tempfile.mkdtemp())
        browser_dir = directory / 'chromium-1243'
        browser_dir.mkdir()
        if marker:
            (browser_dir / 'INSTALLATION_COMPLETE').write_text('', encoding='utf-8')
        if binary:
            complete_layout(browser_dir)
        if shell:
            shell_dir = directory / 'chromium_headless_shell-1243'
            shell_dir.mkdir()
            (shell_dir / 'INSTALLATION_COMPLETE').write_text('', encoding='utf-8')
            complete_layout(shell_dir, 'chromium-headless-shell')
        return directory

    def test_missing_cache_dir_is_not_ready(self):
        self.assertFalse(chromium_ready(Path(tempfile.mkdtemp()) / 'absent'))

    def test_partial_install_without_marker_is_not_ready(self):
        self.assertFalse(chromium_ready(self.make_cache(binary=True)))

    def test_marker_without_binary_is_not_ready(self):
        self.assertFalse(chromium_ready(self.make_cache(marker=True)))

    def test_complete_install_is_ready(self):
        self.assertTrue(chromium_ready(self.make_cache(marker=True, binary=True)))

    def test_missing_headless_shell_is_not_ready(self):
        self.assertFalse(chromium_ready(self.make_cache(marker=True, binary=True, shell=False)))

    def test_old_revision_does_not_count_as_ready(self):
        cache = self.make_cache(marker=True, binary=True)
        with patch.object(Browser, '_manifest_entry', side_effect=lambda name: {'revision': 'new', 'browserVersion': '153.0.8010.12'}):
            self.assertFalse(chromium_ready(cache))


class SystemBrowserTests(unittest.TestCase):
    def test_system_chrome_avoids_chromium_install(self):
        self.check_launch([], 'chrome', ['chrome'])

    def test_edge_is_tried_when_chrome_cannot_launch(self):
        self.check_launch(['chrome'], 'msedge', ['chrome', 'chrome', 'msedge'])

    def test_bundled_browser_is_fallback_when_system_browsers_fail(self):
        self.check_launch(['chrome', 'msedge'], 'chromium', ['chrome', 'chrome', 'msedge', 'chromium'])

    @unittest.skipUnless(sys.platform == 'win32', 'Windows registry lookup')
    def test_registered_chrome_precedes_installed_edge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chrome = root / 'custom' / 'chrome.exe'
            edge = root / 'programs-x86' / 'Microsoft/Edge/Application/msedge.exe'
            for binary in (chrome, edge):
                binary.parent.mkdir(parents=True, exist_ok=True)
                binary.touch()
            environment = {'PROGRAMFILES': str(root / 'programs'),
                           'PROGRAMFILES(X86)': str(root / 'programs-x86'),
                           'LOCALAPPDATA': str(root / 'local')}
            with patch.dict(browser_module.os.environ, environment), \
                 patch.object(Browser, '_windows_app_paths', side_effect=lambda name: [chrome] if name == 'chrome.exe' else []):
                self.assertEqual(Browser.system_browsers(), [('chrome', chrome), ('msedge', edge)])

    def test_transient_chrome_failure_is_retried_before_edge(self):
        self.check_launch(['chrome-once'], 'chrome', ['chrome', 'chrome'])

    def test_system_browser_crash_tries_other_installed_browser_next(self):
        browser = Browser()
        browser.active_channel = 'chrome'
        with patch.object(browser, 'stop'):
            browser.recover_from_crash()
        self.assertEqual(browser.failed_system_channels, {'chrome'})
        self.assertFalse(browser.use_headless_shell)

    def test_bundled_browser_crash_uses_headless_shell(self):
        browser = Browser()
        browser.active_channel = 'chromium'
        with patch.object(browser, 'stop'):
            browser.recover_from_crash()
        self.assertTrue(browser.use_headless_shell)

    def test_sign_in_window_closes_after_confirmation(self):
        browser = Browser()
        context = SimpleNamespace(close=lambda: None)
        browser.context = context
        browser.page = object()
        browser.headless = False
        with patch.object(context, 'close') as close:
            browser.close_sign_in()
        close.assert_called_once_with()
        self.assertIsNone(browser.context)
        self.assertIsNone(browser.page)

    def test_sign_in_navigation_failure_closes_window(self):
        browser = Browser()
        page = SimpleNamespace(goto=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('navigation failed')))
        with patch.object(browser, 'open', side_effect=lambda **_kwargs: setattr(browser, 'page', page)), \
             patch.object(browser, 'close') as close:
            with self.assertRaisesRegex(RuntimeError, 'navigation failed'):
                browser.open_sign_in()
        close.assert_called_once_with()

    def test_sign_in_verification_requires_authenticated_files_page(self):
        browser = Browser()
        browser.headless = True
        browser.context = object()
        browser.page = SimpleNamespace(goto=lambda *_args, **_kwargs: None,
                                       wait_for_function=lambda *_args, **_kwargs: None)
        with patch.object(browser, '_collect_teams', return_value=[{'id': '1', 'name': 'Team'}]):
            self.assertTrue(browser.verify_sign_in())
        browser.page.wait_for_function = lambda *_args, **_kwargs: (_ for _ in ()).throw(browser_module.PlaywrightTimeout('timeout'))
        self.assertFalse(browser.verify_sign_in())

    def test_sign_in_verification_closes_visible_window_and_reopens_headless(self):
        browser = Browser()
        visible = SimpleNamespace(close=lambda: None)
        browser.context = visible
        browser.headless = False
        page = SimpleNamespace(goto=lambda *_args, **_kwargs: None,
                               wait_for_function=lambda *_args, **_kwargs: None)

        def open_headless(headless):
            self.assertTrue(headless)
            browser.context = object()
            browser.page = page
            browser.headless = True

        with patch.object(visible, 'close') as close, \
             patch.object(browser, 'open', side_effect=open_headless) as open_browser, \
             patch.object(browser, '_collect_teams', return_value=[{'id': '1', 'name': 'Team'}]):
            self.assertTrue(browser.verify_sign_in())
        close.assert_called_once_with()
        open_browser.assert_called_once_with(headless=True)

    def check_launch(self, failures, expected, channels):
        class Context:
            pages = []
            def add_init_script(self, _): pass
            def new_page(self): return object()
            def close(self): pass

        class Chromium:
            executable_path = 'unused-chromium'
            def __init__(self): self.calls = []
            def launch_persistent_context(self, profile, **options):
                self.calls.append((profile, options))
                if options.get('channel') in failures or (
                        'chrome-once' in failures and options.get('channel') == 'chrome'
                        and sum(call[1].get('channel') == 'chrome' for call in self.calls) == 1):
                    raise RuntimeError('system browser could not launch')
                return Context()

        with tempfile.TemporaryDirectory() as directory:
            engine = Chromium()
            browser = Browser(Path(directory))
            browser.playwright = SimpleNamespace(chromium=engine)
            candidates = [('chrome', Path(directory) / 'chrome.exe'), ('msedge', Path(directory) / 'msedge.exe')]
            with patch.object(Browser, 'system_browsers', return_value=candidates), \
                 patch.object(Browser, '_headless_user_agent', return_value='Chrome test agent'), \
                 patch.object(browser_module, 'chromium_ready', return_value=True), \
                 patch.object(Browser, '_install_chromium', side_effect=AssertionError('unexpected download')):
                browser.open(headless=True)
            self.assertEqual(browser.active_channel, expected)
            self.assertEqual(browser.failed_system_channels, set())
            self.assertEqual([options['channel'] for _, options in engine.calls], channels)
            self.assertEqual(Path(engine.calls[-1][0]).name,
                             'chromium-profile' if expected == 'chromium' else f'chromium-profile-{expected}')


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
             patch.object(Browser, '_ensure_browser', side_effect=fake_ensure), \
             patch.object(Browser, '_migrate_legacy_shell'), \
             patch.object(browser_module, 'chromium_ready', return_value=False):
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
             patch.object(Browser, '_migrate_legacy_shell'), \
             patch.object(browser_module, 'chromium_ready', return_value=False), \
             patch.object(browser_module.subprocess, 'run', side_effect=fake_run):
            with self.assertRaises(FigmaError) as ctx:
                Browser._install_chromium()
        message = str(ctx.exception)
        self.assertIn('a: download stalled', message)
        self.assertIn('b: download stalled', message)
        self.assertIn('playwright-installer: Error: Download failure, code=1', message)

    def test_install_cli_last_resort_succeeds(self):
        with patch.object(Browser, '_ordered_hosts', return_value=[]), \
             patch.object(browser_module.subprocess, 'run'), \
             patch.object(Browser, '_migrate_legacy_shell'), \
             patch.object(browser_module, 'chromium_ready', side_effect=[False, True]):
            Browser._install_chromium()

    def test_old_shell_cache_is_moved_to_playwright_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / 'chromium-headless-shell-1243'
            legacy.mkdir()
            complete_layout(legacy, 'chromium-headless-shell')
            (legacy / 'INSTALLATION_COMPLETE').write_text('', encoding='utf-8')
            with patch.object(Browser, 'browser_cache_dir', return_value=root):
                Browser._migrate_legacy_shell()
            self.assertFalse(legacy.exists())
            self.assertTrue((root / 'chromium_headless_shell-1243' / 'INSTALLATION_COMPLETE').exists())

    def test_install_reports_byte_progress(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as bundle:
            bundle.writestr(binary_relative('chromium').as_posix(), 'binary')
            bundle.writestr(binary_relative('chromium-headless-shell').as_posix(), 'binary')
        payload = buffer.getvalue()

        def fake_segment(url, start, end, part, on_bytes=None, attempts=10):
            chunk = payload[start:end + 1]
            part.write_bytes(chunk)
            if on_bytes:
                on_bytes(len(chunk))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'driver' / 'package'
            package.mkdir(parents=True)
            manifest = {"browsers": [
                {"name": "chromium", "revision": "1243", "browserVersion": "153.0.8010.12"},
                {"name": "chromium-headless-shell", "revision": "1243", "browserVersion": "153.0.8010.12"},
            ]}
            (package / 'browsers.json').write_text(json.dumps(manifest), encoding='utf-8')
            with patch.object(Browser, '_ordered_hosts', return_value=[('https://a', 'a')]), \
                 patch.object(Browser, '_content_length', return_value=len(payload)), \
                 patch.object(Browser, '_fetch_segment', side_effect=fake_segment), \
                 patch.object(Browser, 'browser_cache_dir', return_value=root), \
                 patch.object(browser_module, 'compute_driver_executable',
                              return_value=('node', package / 'cli.js')):
                Browser._install_chromium()
                progress = Browser.install_progress()
                self.assertTrue((root / 'chromium-1243' / 'INSTALLATION_COMPLETE').exists())
                self.assertTrue((root / 'chromium_headless_shell-1243' / 'INSTALLATION_COMPLETE').exists())
            self.assertEqual(progress, {'done': len(payload) * 2, 'total': len(payload) * 2})
            self.assertTrue(chromium_ready(root))

    def test_last_segment_attempt_can_finish_successfully(self):
        class Response:
            status = 206
            def __init__(self): self.sent = False
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _):
                if self.sent: return b''
                self.sent = True
                return b'abcd'

        with tempfile.TemporaryDirectory() as directory, patch.object(browser_module, 'urlopen', return_value=Response()):
            part = Path(directory) / 'part'
            Browser._fetch_segment('https://example.com/archive', 0, 3, part, attempts=1)
            self.assertEqual(part.read_bytes(), b'abcd')


if __name__ == '__main__':
    unittest.main()
