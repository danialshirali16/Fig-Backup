import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from playwright._impl._errors import TargetClosedError

from figma_backup.app import Bridge


class Client:
    unavailable_subfolders = {'44'}

    def top_folders(self, team_id):
        return [{'id': '44', 'name': 'Folder'}]

    def walk_tree(self, roots):
        self.unavailable_subfolders.add('44')
        return self.all_files(roots[0]), [[roots[0]]]

    def all_files(self, folder):
        return [{'key': 'a', 'name': 'A', 'editorType': 'figma'},
                {'key': 'b', 'name': 'B', 'editorType': 'figjam'}]

    def files(self, folder_id):
        return self.all_files({'id': folder_id})

    def editor_type(self, file):
        return file['editorType']


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
        return bridge

    def test_queue_totals_and_warning(self):
        bridge = self.make_bridge(Browser())
        with patch('figma_backup.app.TreeArchiveIndex') as index:
            index.return_value.root = Path('/tmp/Fig Backup/Team')
            bridge._run_download({'scope': 'folder', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44', 'name': 'Folder'}})
        state = bridge.status()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual((state['saved'], state['skipped'], state['failed']), (1, 1, 0))
        self.assertEqual([item['status'] for item in state['items']], ['saved', 'skipped'])
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

        browser = ClosingBrowser()
        bridge = self.make_bridge(browser)
        with patch('figma_backup.app.ArchiveIndex'):
            bridge._run_download({'scope': 'file', 'team': {'id': '10', 'name': 'Team'},
                                  'folder': {'id': '44'}, 'file_key': 'a'})
        self.assertEqual(bridge.status()['saved'], 1)
        self.assertEqual(browser.calls, 2)
        self.assertTrue(browser.stopped)


if __name__ == '__main__':
    unittest.main()
