import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from playwright._impl._errors import TargetClosedError

from figma_backup.app import Bridge
from figma_backup.core import BrowserAuthError, FigmaError


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

    def editor_type(self, file):
        return file['editorType']


class FigmaFilesClient(Client):
    def all_files(self, folder):
        return [{'key': 'a', 'name': 'A', 'editorType': 'figma'},
                {'key': 'b', 'name': 'B', 'editorType': 'figma'}]


class Browser:
    def download(self, file, index, progress):
        progress('saving', 'Saving')
        return {'status': 'saved', 'path': '/tmp/A.fig', 'size': 2048}


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
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual((state['saved'], state['skipped'], state['failed']), (2, 1, 0))
        self.assertEqual([item['status'] for item in state['items']], ['saved', 'saved', 'skipped'])
        self.assertTrue(state['warning'])

    def test_browser_close_retries_once(self):
        class ClosingBrowser(Browser):
            calls = 0
            stopped = False

            def download(self, file, index, progress):
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
        with patch('figma_backup.app.ArchiveIndex'):
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
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual((state['failed'], state['saved']), (1, 1))
        self.assertEqual([item['status'] for item in state['items']], ['failed', 'saved'])

    def test_browser_auth_error_stops_queue_with_attention(self):
        class AuthRequiredBrowser(Browser):
            def download(self, file, index, progress):
                raise BrowserAuthError('Browser sign-in is required. Use the Sign in button, then retry.')

        bridge = self.make_bridge(AuthRequiredBrowser())
        bridge.client = FigmaFilesClient()
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
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


class InstallerBrowser:
    def __init__(self, fail=False):
        self.release = threading.Event()
        self.fail = fail
        self.calls = 0

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
        self.assertEqual(bridge.status()['browser'], {'phase': 'setting_up', 'message': ''})

    def test_install_success_marks_ready(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        self.assertEqual(bridge.install_browser(), {'started': True})
        self.assertEqual(bridge.status()['browser']['phase'], 'setting_up')
        browser.release.set()
        self.settle(bridge, 'ready')

    def test_double_install_is_guarded(self):
        browser = InstallerBrowser()
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        self.assertEqual(bridge.install_browser(), {'started': True})
        self.assertEqual(bridge.install_browser(), {'started': False})
        browser.release.set()
        self.settle(bridge, 'ready')
        self.assertEqual(browser.calls, 1)

    def test_install_failure_carries_message(self):
        browser = InstallerBrowser(fail=True)
        bridge = BridgeTests.make_bridge(browser)
        bridge.executor = self.executor
        bridge.install_browser()
        browser.release.set()
        self.settle(bridge, 'failed')
        self.assertEqual(bridge.status()['browser']['message'], 'Automatic Chromium installation failed: offline')


if __name__ == '__main__':
    unittest.main()
