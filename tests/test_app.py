import ctypes
import json
import threading
import time
import tempfile
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from playwright._impl._errors import TargetClosedError

import figma_backup.app as app_module
from figma_backup.app import Bridge, _reveal_in_explorer
from figma_backup.core import ArchiveIndex, BrowserAuthError, FigmaError, FileConflict, PreferencesStore, TreeArchiveIndex


class Client:
    unavailable_subfolders = {'44'}

    def top_folders(self, team_id):
        return [{'id': '44', 'name': 'Folder'}]

    def walk_tree(self, roots):
        self.unavailable_subfolders.add('44')
        return self.all_files(roots[0]), [[roots[0]]]

    def all_files(self, folder):
        return [{'key': 'a', 'name': 'A', 'editorType': 'figma'},
                {'key': 'b', 'name': 'B', 'editorType': 'figjam'},
                {'key': 'c', 'name': 'C', 'editorType': 'library'}]

    def files(self, folder_id):
        return self.all_files({'id': folder_id})

    def apply_cached_types(self, files):
        return None

    def flush_types(self):
        return None

    def editor_type(self, file):
        return file['editorType']


class FigmaFilesClient(Client):
    def all_files(self, folder):
        return [{'key': 'a', 'name': 'A', 'editorType': 'figma'},
                {'key': 'b', 'name': 'B', 'editorType': 'figma'}]


class Browser:
    def download(self, file, index, progress, overwrite=False):
        progress('saving', 'Saving')
        return {'status': 'saved', 'path': '/tmp/A.fig', 'size': 2048}


class EditorTypeClient:
    def __init__(self, error=None):
        self.unavailable_subfolders = set()
        self.lock = threading.Lock()
        self.calls = 0
        self.error = error

    def files(self, folder_id):
        return [{'key': f'k{index}', 'name': f'F{index}'} for index in range(12)]

    def apply_cached_types(self, files):
        return None

    def flush_types(self):
        return None

    def editor_type(self, file):
        with self.lock:
            self.calls += 1
        if self.error:
            raise self.error
        return 'figjam'


class ForbiddenOnceBrowser(Browser):
    """Refuses the first file the way Figma's editor does, then works."""

    def __init__(self):
        self.seen = 0

    def download(self, file, index, progress, overwrite=False):
        self.seen += 1
        if self.seen == 1:
            raise FigmaError('Figma refused to open this file (HTTP 403).', 403)
        progress('saving', 'Saving')
        return {'status': 'saved', 'path': '/tmp/B.fig', 'size': 2048}


class IntPtrLike:
    """Stands in for pythonnet's System.IntPtr on Windows.

    pythonnet explicitly refuses to convert IntPtr to a Python int, and pywebview
    always calls .ToInt32() on a Form handle. A bare int(handle) therefore raises,
    which would break resizing on the deliberately frameless Windows window.
    """

    def __init__(self, value):
        self._value = value

    def __int__(self):
        raise TypeError('cannot convert System.IntPtr to int')

    def __bool__(self):
        return True

    def ToInt64(self):
        return self._value

    def ToInt32(self):
        return self._value


class WindowsResizeTests(unittest.TestCase):
    """Runs on every platform by standing in for the Windows runtime."""

    def setUp(self):
        self.sent = {}
        sent = self.sent

        class User32:
            def ReleaseCapture(self):
                sent['released'] = True

            def SendMessageW(self, hwnd, message, wparam, lparam):
                sent['call'] = (hwnd, message, wparam, lparam)

        class Windll:
            user32 = User32()

        class Native:
            def __init__(self, value):
                self.Handle = IntPtrLike(value)

        class Window:
            def __init__(self, value):
                self.native = Native(value)

        self.patch = [
            patch.object(app_module.sys, 'platform', 'win32'),
            patch.object(app_module.ctypes, 'windll', Windll(), create=True),
            patch.object(app_module.webview, 'windows', [Window(0x1A2B)]),
        ]
        for item in self.patch:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patch])

    def test_resize_hands_a_real_handle_to_the_sizing_loop(self):
        bridge = Bridge.__new__(Bridge)
        bridge.maximized = False
        self.assertEqual(bridge.begin_resize(12), {'ok': True})
        self.assertTrue(self.sent.get('released'))
        hwnd, message, wparam, lparam = self.sent['call']
        self.assertEqual(hwnd, 0x1A2B, 'the HWND must survive the IntPtr conversion')
        self.assertEqual(message, 0xA1, 'WM_NCLBUTTONDOWN')
        self.assertEqual(wparam, 12, 'HTTOP')

    def test_resize_is_refused_when_maximized_or_off_edge(self):
        bridge = Bridge.__new__(Bridge)
        bridge.maximized = True
        self.assertEqual(bridge.begin_resize(12), {'ok': False})
        bridge.maximized = False
        self.assertEqual(bridge.begin_resize(4), {'ok': False})
        self.assertNotIn('call', self.sent)


class BridgeTests(unittest.TestCase):
    @staticmethod
    def make_bridge(browser):
        bridge = Bridge.__new__(Bridge)
        bridge.client = Client()
        bridge.browser = browser
        bridge.lock = threading.Lock()
        bridge.stop_requested = False
        bridge.state = {'running': True, 'phase': 'scanning', 'items': [], 'current': 0,
                        'total': 0, 'saved': 0, 'existing': 0, 'skipped': 0, 'failed': 0,
                        'message': '', 'warning': '', 'finished': False}
        bridge.browser_state = {'phase': 'ready', 'message': ''}
        return bridge

    def test_queue_totals_and_warning(self):
        bridge = self.make_bridge(Browser())
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
            index.return_value.plan.return_value = (None, None)
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual((state['saved'], state['skipped'], state['failed']), (2, 1, 0))
        self.assertEqual([item['status'] for item in state['items']], ['saved', 'saved', 'skipped'])
        self.assertTrue(state['warning'])

    def test_folder_download_destination_is_selected_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'Downloads'
            bridge = self.make_bridge(Browser())
            with patch('figma_backup.app.TreeArchiveIndex',
                       side_effect=lambda team: TreeArchiveIndex(team, root / 'Support', downloads)):
                bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                      'folder': {'id': '44', 'name': 'Folder'}})
            self.assertEqual(Path(bridge.status()['destination']), downloads / 'Fig Backup/Team/Folder')

    def test_browser_close_retries_once(self):
        class ClosingBrowser(Browser):
            calls = 0
            stopped = False

            def download(self, file, index, progress, overwrite=False):
                self.calls += 1
                if self.calls == 1:
                    raise TargetClosedError('closed')
                return super().download(file, index, progress)

            def stop(self):
                self.stopped = True

            def recover_from_crash(self):
                self.stop()
                self.use_headless_shell = True

        browser = ClosingBrowser()
        bridge = self.make_bridge(browser)
        with patch('figma_backup.app.ArchiveIndex') as index:
            index.return_value.plan.return_value = (None, None)
            bridge._run_download({'scope': 'file', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44'}, 'file_key': 'a'})
        self.assertEqual(bridge.status()['saved'], 1)
        self.assertEqual(browser.calls, 2)
        self.assertTrue(browser.stopped)
        self.assertTrue(browser.use_headless_shell)

    def test_api_403_fails_file_but_queue_continues(self):
        class RestrictedClient(FigmaFilesClient):
            def editor_type(self, file):
                if file['key'] == 'a':
                    raise FigmaError('Figma API HTTP 403: /v1/files/a?depth=1', 403)
                return 'figma'

        bridge = self.make_bridge(Browser())
        bridge.client = RestrictedClient()
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
            index.return_value.plan.return_value = (None, None)
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual((state['failed'], state['saved']), (1, 1))
        self.assertEqual([item['status'] for item in state['items']], ['failed', 'saved'])

    def test_stop_during_scan_reports_stopped(self):
        class EmptyClient(Client):
            def all_files(self, folder):
                return []

        bridge = self.make_bridge(Browser())
        bridge.client = EmptyClient()
        bridge.stop_requested = True
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
            index.return_value.plan.return_value = (None, None)
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'stopped')
        self.assertFalse(state['running'])
        self.assertTrue(state['finished'])

    def test_files_listing_does_not_block_on_editor_types(self):
        """The listing must come back before any per-file /meta call is made."""
        bridge = self.make_bridge(Browser())
        client = EditorTypeClient()
        bridge.client = client
        result = bridge.files('44')
        self.assertEqual(len(result['files']), 12)
        self.assertEqual(client.calls, 0, 'the listing must not spend API calls on icons')
        self.assertTrue(all('editorType' not in file for file in result['files']))

    def test_file_types_resolves_every_requested_key(self):
        bridge = self.make_bridge(Browser())
        client = EditorTypeClient()
        bridge.client = client
        keys = [f'k{index}' for index in range(12)]
        types = bridge.file_types(keys)
        self.assertEqual(sorted(types), sorted(keys), 'every requested key gets an answer')
        self.assertEqual(set(types.values()), {'figjam'})
        self.assertEqual(client.calls, 12)

    def test_file_types_deduplicates_and_ignores_junk(self):
        bridge = self.make_bridge(Browser())
        client = EditorTypeClient()
        bridge.client = client
        types = bridge.file_types(['a', 'a', '', None, 'b'])
        self.assertEqual(sorted(types), ['a', 'b'])
        self.assertEqual(client.calls, 2)

    def test_file_types_survives_rate_limit(self):
        """A 429 must still answer every key, or rows keep showing a skeleton."""
        bridge = self.make_bridge(Browser())
        bridge.client = EditorTypeClient(error=FigmaError('Figma API HTTP 429: slow down', 429))
        keys = [f'k{index}' for index in range(12)]
        types = bridge.file_types(keys)
        self.assertEqual(sorted(types), sorted(keys))
        self.assertTrue(all(value is None for value in types.values()))

    def test_browser_auth_error_stops_queue_with_attention(self):
        class AuthRequiredBrowser(Browser):
            def download(self, file, index, progress, overwrite=False):
                raise BrowserAuthError('Browser sign-in is required. Use the Sign in button, then retry.')

        bridge = self.make_bridge(AuthRequiredBrowser())
        bridge.client = FigmaFilesClient()
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
            index.return_value.plan.return_value = (None, None)
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'attention')
        self.assertEqual(state['failed'], 1)
        self.assertEqual([item['status'] for item in state['items']], ['failed', 'queued'])
        self.assertFalse(state['running'])

    def test_shutdown_forces_exit_when_download_is_stuck(self):
        class StuckExecutor:
            def submit(self, *args, **kwargs):
                raise RuntimeError('cannot queue')

            def shutdown(self, wait=False):
                pass

        bridge = self.make_bridge(Browser())
        bridge.executor = StuckExecutor()
        exits = []
        bridge.shutdown(grace_seconds=0.05, exit_now=exits.append)
        self.assertTrue(bridge.stop_requested)
        self.assertEqual(exits, [0])

    def test_shutdown_stops_browser_when_idle(self):
        class StoppingBrowser(Browser):
            stopped = False

            def stop(self):
                self.stopped = True

        browser = StoppingBrowser()
        bridge = self.make_bridge(browser)
        bridge.executor = ThreadPoolExecutor(max_workers=1)
        bridge.state['running'] = False
        exits = []
        bridge.shutdown(grace_seconds=1.0, exit_now=exits.append)
        self.assertTrue(browser.stopped)
        self.assertEqual(exits, [0])


@unittest.skipUnless(sys.platform == 'win32', 'Windows Explorer integration')
class RevealDownloadTests(unittest.TestCase):
    def test_windows_shell_parses_unicode_filename_for_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / '☄️  Hyper Design.fig'
            file.touch()
            with patch.object(ctypes.windll.shell32, 'SHOpenFolderAndSelectItems', return_value=0) as open_selected:
                _reveal_in_explorer(file)
            self.assertEqual(open_selected.call_count, 1)
            self.assertEqual(open_selected.call_args.args[1:], (0, None, 0))
            self.assertTrue(open_selected.call_args.args[0])

    def test_reveals_exact_file_with_spaces_and_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            downloads = Path(directory) / 'Downloads'
            downloads.mkdir()
            file = downloads / '☄️  Hyper Design.fig'
            file.touch()
            with patch('figma_backup.app.DOWNLOADS', downloads), \
                 patch('figma_backup.app._reveal_in_explorer') as reveal:
                self.assertEqual(Bridge.__new__(Bridge).open_path(str(file)), {'opened': True})
            reveal.assert_called_once_with(file.resolve())

    def test_rejects_paths_outside_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'Downloads'
            downloads.mkdir()
            other = root / 'other.fig'
            other.touch()
            with patch('figma_backup.app.DOWNLOADS', downloads), \
                 patch('figma_backup.app._reveal_in_explorer') as reveal:
                with self.assertRaisesRegex(FigmaError, 'outside Downloads'):
                    Bridge.__new__(Bridge).open_path(str(other))
            reveal.assert_not_called()


class InstallerBrowser:
    def __init__(self, fail=False):
        self.release = threading.Event()
        self.fail = fail
        self.calls = 0

    def install_progress(self):
        return {"done": 0, "total": 0}

    def _install_chromium(self):
        self.calls += 1
        self.release.wait(timeout=5)
        if self.fail:
            raise FigmaError('Automatic Chromium installation failed: offline')

    def stop(self):
        pass


class BrowserInstallTests(unittest.TestCase):
    def setUp(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

    def tearDown(self):
        self.executor.shutdown(wait=True)

    def test_installed_browser_skips_initial_chromium_setup(self):
        with patch('figma_backup.app.Browser') as browser_class, \
             patch('figma_backup.app.TokenStore') as token_class, \
             patch('figma_backup.app.chromium_ready', return_value=False):
            browser_class.return_value.system_browsers.return_value = [('chrome', Path('chrome.exe'))]
            token_class.return_value.load.return_value = None
            bridge = Bridge()
        try:
            self.assertEqual(bridge.browser_state['phase'], 'ready')
            self.assertEqual(bridge.browser_state['source'], 'chrome')
        finally:
            bridge.executor.shutdown(wait=False)

    def settle(self, bridge, phase, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if bridge.status()['browser']['phase'] == phase:
                return
            time.sleep(0.01)
        self.fail(f'browser_state never reached {phase}: {bridge.status()["browser"]}')

    def test_status_includes_browser_state(self):
        bridge = BridgeTests.make_bridge(InstallerBrowser())
        bridge.executor = self.executor
        bridge.browser_state = {'phase': 'setting_up', 'message': ''}
        self.assertEqual(bridge.status()['browser'],
                         {'phase': 'setting_up', 'message': '', 'done': 0, 'total': 0})

    def test_system_browser_fallback_exposes_install_progress_and_error(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.browser_state = {'phase': 'ready', 'message': '', 'source': 'chrome'}
        browser.installing = True
        self.assertEqual(bridge.status()['browser']['phase'], 'setting_up')
        browser.installing = False
        browser.install_error = 'Chromium download failed'
        self.assertEqual(bridge.status()['browser']['phase'], 'failed')
        self.assertEqual(bridge.status()['browser']['message'], 'Chromium download failed')

    def test_successful_system_browser_recovers_failed_install_state(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.browser_state = {'phase': 'failed', 'message': 'Chromium download failed'}
        browser.active_channel = 'msedge'
        self.assertEqual(bridge.status()['browser'],
                         {'phase': 'ready', 'message': '', 'source': 'msedge'})

    def test_install_success_marks_ready(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        with patch('figma_backup.app.chromium_ready', return_value=True):
            self.assertEqual(bridge.install_browser(), {'started': True})
            self.assertEqual(bridge.status()['browser']['phase'], 'setting_up')
            browser.release.set()
            self.settle(bridge, 'ready')

    def test_double_install_is_guarded(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        with patch('figma_backup.app.chromium_ready', return_value=True):
            self.assertEqual(bridge.install_browser(), {'started': True})
            self.assertEqual(bridge.install_browser(), {'started': False})
            browser.release.set()
            self.settle(bridge, 'ready')
        self.assertEqual(browser.calls, 1)

    def test_install_does_not_mark_incomplete_browser_ready(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        with patch('figma_backup.app.chromium_ready', return_value=False):
            bridge.install_browser()
            browser.release.set()
            self.settle(bridge, 'failed')
        self.assertIn('required browser files are missing', bridge.status()['browser']['message'])

    def test_install_failure_carries_message(self):
        browser = InstallerBrowser(fail=True)
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        bridge.install_browser()
        browser.release.set()
        self.settle(bridge, 'failed')
        self.assertEqual(bridge.status()['browser']['message'], 'Automatic Chromium installation failed: offline')


class RequiredSetupTests(unittest.TestCase):
    def test_browser_check_failure_blocks_first_step(self):
        class BrokenBrowser:
            def open(self, headless):
                raise RuntimeError('browser could not start')

        with ThreadPoolExecutor(max_workers=1) as executor:
            bridge = Bridge.__new__(Bridge)
            bridge.executor = executor
            bridge.browser = BrokenBrowser()
            bridge.lock = threading.Lock()
            bridge.browser_state = {'phase': 'ready', 'message': ''}
            bridge.browser_verified = False
            with self.assertRaisesRegex(RuntimeError, 'browser could not start'):
                bridge.verify_browser()
            self.assertFalse(bridge.browser_verified)
            self.assertEqual(bridge.browser_state['phase'], 'failed')

    def test_completion_requires_browser_token_and_real_sign_in(self):
        class SetupBrowser:
            active_channel = None
            signed_in = False

            def open(self, headless):
                self.active_channel = 'chrome'

            def close(self):
                pass

            def verify_sign_in(self):
                return self.signed_in

        with tempfile.TemporaryDirectory() as directory, ThreadPoolExecutor(max_workers=1) as executor:
            bridge = Bridge.__new__(Bridge)
            bridge.executor = executor
            bridge.browser = SetupBrowser()
            bridge.browser_verified = False
            bridge.token_verified = False
            bridge.browser_state = {'phase': 'ready', 'message': '', 'source': 'chrome'}
            bridge.lock = threading.Lock()
            bridge.client = type('Client', (), {'me': lambda self: {'handle': 'Tester'}})()
            bridge.preferences_store = PreferencesStore(Path(directory))

            with self.assertRaisesRegex(FigmaError, 'Setup completion must be verified'):
                bridge.save_preferences({'onboarding_complete': True})
            with self.assertRaisesRegex(FigmaError, 'Verify the browser'):
                bridge.complete_setup()
            with self.assertRaisesRegex(FigmaError, 'Complete all three setup steps'):
                bridge.start_download({'scope': 'team', 'team': {'id': '1'}})
            self.assertEqual(bridge.verify_browser(), {'ready': True, 'source': 'chrome'})
            with self.assertRaisesRegex(FigmaError, 'Verify the browser'):
                bridge.complete_setup()
            self.assertEqual(bridge.verify_token(), {'name': 'Tester'})
            self.assertEqual(bridge.complete_setup(), {'completed': False})
            self.assertEqual(bridge.preferences_store.load()['setup_version'], 0)
            bridge.browser.signed_in = True
            result = bridge.complete_setup()
            self.assertTrue(result['completed'])
            self.assertTrue(result['preferences']['onboarding_complete'])
            self.assertEqual(result['preferences']['setup_version'], 2)
            reset = bridge.begin_setup()
            self.assertFalse(reset['preferences']['onboarding_complete'])
            self.assertEqual(reset['preferences']['setup_version'], 0)
            with self.assertRaisesRegex(FigmaError, 'Verify the browser'):
                bridge.complete_setup()

    def test_replacing_token_restarts_required_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = Bridge.__new__(Bridge)
            bridge.preferences_store = PreferencesStore(Path(directory))
            bridge.preferences_store.save({'onboarding_complete': True, 'setup_version': 2})
            bridge.token_store = type('Store', (), {'save': lambda self, token: None})()
            bridge.token = 'old-token'
            bridge.client = None
            bridge.browser_verified = True
            bridge.token_verified = True
            client = type('Client', (), {'me': lambda self: {'handle': 'Tester'}})()
            with patch('figma_backup.app.FigmaClient', return_value=client):
                result = bridge.save_token('new-token')
            self.assertTrue(result['setup_required'])
            self.assertFalse(bridge.preferences_store.load()['onboarding_complete'])
            self.assertFalse(bridge.browser_verified)
            self.assertFalse(bridge.token_verified)


if __name__ == '__main__':
    unittest.main()


class EditorForbiddenTests(unittest.TestCase):
    """A 403 on one file must not abort the queue or reset the setup.

    It used to raise BrowserAuthError, which set phase="attention" and routed
    the UI into the wizard — and openWizard() calls begin_setup(), which wipes
    onboarding_complete on disk. One inaccessible file cost the user their whole
    completed setup.
    """

    def test_a_403_fails_only_that_file(self):
        bridge = BridgeTests.make_bridge(ForbiddenOnceBrowser())
        bridge.client = FigmaFilesClient()
        with patch('figma_backup.app.TreeArchiveIndex'):
            index = unittest.mock.MagicMock()
            index.root = Path('/tmp/Fig Backup/Team')
            index.folder_path.return_value = Path('/tmp/Fig Backup/Team')
            index.target.return_value = (Path('/tmp/Fig Backup/Team/A.fig'), False)
            index.plan.return_value = (None, None)
            with patch('figma_backup.app.TreeArchiveIndex', return_value=index):
                bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                      'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done', 'the run must finish, not stop for attention')
        self.assertEqual(state['failed'], 1)
        self.assertEqual(state['saved'], 1, 'the other file must still be saved')

    def test_a_403_row_offers_retry_instead_of_sign_in(self):
        bridge = BridgeTests.make_bridge(ForbiddenOnceBrowser())
        bridge.client = FigmaFilesClient()
        with patch('figma_backup.app.TreeArchiveIndex'):
            index = unittest.mock.MagicMock()
            index.root = Path('/tmp/Fig Backup/Team')
            index.folder_path.return_value = Path('/tmp/Fig Backup/Team')
            index.target.return_value = (Path('/tmp/Fig Backup/Team/A.fig'), False)
            index.plan.return_value = (None, None)
            with patch('figma_backup.app.TreeArchiveIndex', return_value=index):
                bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                      'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertNotEqual(state['phase'], 'attention', 'attention is what routes to the wizard')
        failed = [item for item in state['items'] if item['status'] == 'failed']
        self.assertEqual(len(failed), 1)
        self.assertIn('403', failed[0]['detail'])


class ConflictBrowser(Browser):
    """Resolves the destination the way a real index does, so conflicts are real."""

    def __init__(self, taken=()):
        self.taken = set(taken)
        self.calls = []

    def download(self, file, index, progress, overwrite=False):
        self.calls.append((file['key'], overwrite))
        wanted, existing = index.plan(file)
        if existing is not None and not overwrite:
            raise FileConflict(wanted, existing)
        progress('saving', 'Saving')
        return {'status': 'saved', 'path': str(wanted), 'size': 2048}


class OneFileClient(Client):
    """A team with exactly one file, so a run pauses on the first one it meets."""

    def all_files(self, folder):
        return [{'key': 'a', 'name': 'A', 'editorType': 'figma'}]


class FileConflictTests(unittest.TestCase):
    """A name clash must pause the run, not silently rename or clobber."""

    def setUp(self):
        self.browser = ConflictBrowser()
        self.bridge = BridgeTests.make_bridge(self.browser)
        self.bridge.client = OneFileClient()
        # make_bridge bypasses __init__, so give it the two attributes the
        # conflict path touches. A mocked executor means resume stays under the
        # test's control instead of firing on a background thread.
        self.bridge._run = None
        self.bridge.executor = unittest.mock.MagicMock()
        self.taken = Path('/tmp/Fig Backup/Team/A.fig')
        self.wanted = Path('/tmp/Fig Backup/Team/A.fig')
        patcher = patch('figma_backup.app.TreeArchiveIndex')
        self.archive_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.archive = self.archive_cls.return_value
        self.archive.root = Path('/tmp/Fig Backup/Team')
        self.archive.folder_path.return_value = Path('/tmp/Fig Backup/Team')
        self.archive.plan.return_value = (self.wanted, self.taken)

    def _run(self):
        self.bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                   'folder': {'id': '44', 'name': 'Folder'}})
        return self.bridge.status()

    def test_a_clash_pauses_the_run_and_asks(self):
        state = self._run()
        self.assertEqual(state['phase'], 'conflict', 'the run must wait, not decide for the user')
        self.assertFalse(state['finished'])
        self.assertTrue(state['running'], 'the run is still alive, just waiting')
        self.assertEqual(state['conflict']['existing'], 'A.fig')
        self.assertEqual(state['conflict']['name'], 'A')
        self.assertEqual(state['conflict']['key'], 'a')

    def test_nothing_is_downloaded_before_the_user_answers(self):
        self._run()
        self.assertEqual(self.browser.calls, [], 'no copy may start while the question is open')

    def test_the_paused_item_is_marked_waiting(self):
        state = self._run()
        self.assertEqual(state['items'][0]['status'], 'conflict')

    def test_overwrite_reaches_the_index(self):
        self._run()
        self.bridge.resolve_conflict('overwrite')
        self.bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                   'folder': {'id': '44', 'name': 'Folder'}}, 0, {'a': 'overwrite'})
        self.assertEqual(self.browser.calls[-1], ('a', True), 'overwrite must reach the index')

    def test_rename_keeps_both_files(self):
        self._run()
        self.bridge.resolve_conflict('rename')
        self.bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                   'folder': {'id': '44', 'name': 'Folder'}}, 0, {'a': 'rename'})
        self.assertEqual(self.browser.calls[-1], ('a', False), 'rename keeps both, so no overwrite')

    def test_cancel_skips_the_file_and_continues(self):
        self._run()
        self.bridge.resolve_conflict('cancel')
        state = self.bridge.status()
        self.assertEqual(state['items'][0]['status'], 'skipped')
        self.assertEqual(state['phase'], 'downloading', 'the queue carries on')
        self.assertIsNone(state['conflict'], 'the question must be cleared')
        self.assertEqual(state['skipped'], 1)

    def test_resolving_without_a_question_is_an_error(self):
        with self.assertRaisesRegex(FigmaError, 'No file is waiting'):
            self.bridge.resolve_conflict('overwrite')

    def test_an_unknown_choice_is_rejected(self):
        self._run()
        with self.assertRaisesRegex(FigmaError, 'overwrite, rename, or cancel'):
            self.bridge.resolve_conflict('maybe')

    def test_a_rejected_choice_keeps_the_question_open(self):
        self._run()
        with self.assertRaises(FigmaError):
            self.bridge.resolve_conflict('maybe')
        self.assertEqual(self.bridge.status()['conflict']['key'], 'a')

    def test_stopping_while_paused_ends_the_run(self):
        self._run()
        self.bridge.stop_download()
        state = self.bridge.status()
        self.assertEqual(state['phase'], 'stopped')
        self.assertIsNone(state['conflict'], 'the dialog must not stay open with no way out')
        self.assertTrue(state['finished'])

    def test_an_already_indexed_file_is_not_a_clash(self):
        with tempfile.TemporaryDirectory() as directory:
            support, downloads = Path(directory) / 'support', Path(directory) / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'a': 'A.fig'}}), encoding='utf-8')
            index = ArchiveIndex(support=support, downloads=downloads)
            wanted, taken = index.plan({'key': 'a', 'name': 'A', 'editorType': 'figma'})
            self.assertIsNone(wanted)
            self.assertIsNone(taken, 'our own earlier copy is "already saved", not a question')

    def test_a_different_file_with_the_same_name_is_a_clash(self):
        with tempfile.TemporaryDirectory() as directory:
            support, downloads = Path(directory) / 'support', Path(directory) / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (downloads / 'Other.fig').write_bytes(b'x' * 2048)
            index = ArchiveIndex(support=support, downloads=downloads)
            wanted, taken = index.plan({'key': 'zzz', 'name': 'Other', 'editorType': 'figma'})
            self.assertEqual(wanted.name, 'Other.fig')
            self.assertEqual(taken.name, 'Other.fig')

    def test_plan_reports_nothing_when_the_name_is_free(self):
        with tempfile.TemporaryDirectory() as directory:
            support, downloads = Path(directory) / 'support', Path(directory) / 'Downloads'
            support.mkdir(); downloads.mkdir()
            index = ArchiveIndex(support=support, downloads=downloads)
            wanted, taken = index.plan({'key': 'new', 'name': 'Fresh', 'editorType': 'figma'})
            self.assertEqual(wanted.name, 'Fresh.fig')
            self.assertIsNone(taken)

    def test_overwrite_policy_claims_the_wanted_name(self):
        with tempfile.TemporaryDirectory() as directory:
            support, downloads = Path(directory) / 'support', Path(directory) / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (downloads / 'A.fig').write_bytes(b'x' * 2048)
            # Two independent indexes: the first call records a mapping for its
            # key, so reusing the key would take the already-indexed path.
            renamed = ArchiveIndex(support=support, downloads=downloads)
            self.assertEqual(
                renamed.target({'key': 'k1', 'name': 'A', 'editorType': 'figma'})[0].name,
                'A(1).fig', 'rename is the default')
            replaced = ArchiveIndex(support=support, downloads=downloads)
            self.assertEqual(
                replaced.target({'key': 'k2', 'name': 'A', 'editorType': 'figma'}, overwrite=True)[0].name,
                'A.fig', 'overwrite claims the name that is already there')
