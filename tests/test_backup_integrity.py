"""Exercise conflict answers through the Bridge, Browser and real disk indexes."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from figma_backup.app import Bridge
from figma_backup.browser import Browser
from figma_backup.core import ArchiveIndex, TreeArchiveIndex


class BackupConflictIntegrationTests(unittest.TestCase):
    OLD = b'PK-old-copy' * 256
    NEW = b'PK-new-copy' * 256

    def run_conflict(self, root, tree, choice, payload=None):
        support, downloads = root / 'Support', root / 'Downloads'
        downloads.mkdir()
        team = {'id': '10', 'name': 'Team'}
        folder = {'id': '20', 'name': 'Folder'}
        file = {'key': 'new', 'name': 'Board', 'editorType': 'figma'}
        if tree:
            file['_folder_path'] = [folder]
            archive = TreeArchiveIndex(team, support, downloads)
            destination = archive.folder_path([folder]) / 'Board.fig'
            destination.parent.mkdir(parents=True, exist_ok=True)
            archive.files = {'old': destination.relative_to(archive.root).as_posix()}
            archive._save()
        else:
            archive = ArchiveIndex(support, downloads)
            destination = downloads / 'Board.fig'
            support.mkdir()
            archive.names = {'old': destination.name}
            archive.path.write_text(json.dumps({'version': 1, 'files': archive.names}), encoding='utf-8')
        destination.write_bytes(self.OLD)
        before_index = archive.path.read_bytes()
        download = SimpleNamespace(
            suggested_filename='Board.fig',
            save_as=MagicMock(side_effect=lambda name: Path(name).write_bytes(
                self.NEW if payload is None else payload)),
        )
        page = MagicMock()
        page.url = 'https://www.figma.com/design/new'
        page.goto.return_value = None
        page.expect_download.return_value.__enter__.return_value.value = download
        browser = Browser(support)
        browser.context, browser.page = object(), page
        browser._save_local_copy = lambda: None
        client = SimpleNamespace(
            unavailable_subfolders=set(),
            files=lambda _id: [file],
            walk_tree=lambda _roots: ([file], [[folder]]),
            editor_type=lambda value: value['editorType'],
            flush_types=lambda: None,
        )
        bridge = Bridge.__new__(Bridge)
        bridge.browser = browser
        bridge._required = lambda: client
        bridge.preferences_store = SimpleNamespace(load=lambda: {
            'onboarding_complete': True, 'setup_version': 2,
        })
        bridge.lock = threading.Lock()
        bridge.state = {'running': False}
        bridge.executor = MagicMock()
        bridge._run = None
        selection = {'scope': 'folder' if tree else 'file', 'team': team, 'folder': folder}
        if not tree:
            selection['file_key'] = file['key']
        with patch('figma_backup.app.TreeArchiveIndex', return_value=archive), \
                patch('figma_backup.app.ArchiveIndex', return_value=archive), \
                patch('figma_backup.app.DOWNLOADS', downloads):
            bridge.start_download(selection)
            pending = bridge.executor.submit.call_args
            pending.args[0](*pending.args[1:], **pending.kwargs)
            self.assertEqual(bridge.state['phase'], 'conflict')
            download.save_as.assert_not_called()
            self.assertEqual(archive.path.read_bytes(), before_index)
            bridge.resolve_conflict(choice)
            pending = bridge.executor.submit.call_args
            pending.args[0](*pending.args[1:], **pending.kwargs)
        reloaded = (TreeArchiveIndex(team, support, downloads) if tree
                    else ArchiveIndex(support, downloads))
        owners = reloaded.files if tree else reloaded.names
        return bridge.state, destination, owners, download, before_index, archive.path

    def test_conflict_answers_save_the_requested_copy_or_preserve_the_old_copy(self):
        for tree in (False, True):
            for choice in ('overwrite', 'rename', 'cancel'):
                with self.subTest(tree=tree, choice=choice), tempfile.TemporaryDirectory() as temporary:
                    state, destination, owners, download, _, _ = self.run_conflict(
                        Path(temporary), tree, choice)
                    self.assertTrue(state['finished'])
                    self.assertEqual(state['phase'], 'done')
                    if choice == 'overwrite':
                        self.assertEqual(destination.read_bytes(), self.NEW)
                        self.assertEqual(set(owners), {'new'})
                        self.assertEqual(Path(owners['new']).name, 'Board.fig')
                    elif choice == 'rename':
                        self.assertEqual(destination.read_bytes(), self.OLD)
                        self.assertEqual((destination.parent / 'Board(1).fig').read_bytes(), self.NEW)
                        self.assertEqual(set(owners), {'old', 'new'})
                        self.assertEqual(Path(owners['new']).name, 'Board(1).fig')
                    else:
                        self.assertEqual(destination.read_bytes(), self.OLD)
                        self.assertEqual(set(owners), {'old'})
                        self.assertEqual(state['items'][0]['status'], 'skipped')
                        download.save_as.assert_not_called()
                    if choice != 'cancel':
                        self.assertEqual((state['saved'], state['existing']), (1, 0))
                        download.save_as.assert_called_once()

    def test_invalid_overwrite_never_claims_or_changes_the_previous_backup(self):
        for tree in (False, True):
            with self.subTest(tree=tree), tempfile.TemporaryDirectory() as temporary:
                state, destination, owners, _, before, index_path = self.run_conflict(
                    Path(temporary), tree, 'overwrite', b'<html>failure</html>' * 128)
                self.assertEqual(destination.read_bytes(), self.OLD)
                self.assertEqual(index_path.read_bytes(), before)
                self.assertEqual(set(owners), {'old'})
                self.assertEqual(state['items'][0]['status'], 'failed')
                self.assertEqual((state['saved'], state['failed']), (0, 1))
                self.assertFalse(destination.with_name(destination.name + '.partial').exists())


if __name__ == '__main__':
    unittest.main()
