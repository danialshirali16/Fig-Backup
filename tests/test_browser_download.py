import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from figma_backup.browser import Browser
from figma_backup.core import FigmaError


class DownloadValidationTests(unittest.TestCase):
    def test_download_extension_must_match_editor_type(self):
        for editor_type, extension, wrong_extension in (
            ('figma', '.fig', '.jam'),
            ('figjam', '.jam', '.deck'),
            ('slides', '.deck', '.fig'),
        ):
            with self.subTest(editor_type=editor_type), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / f'Board{extension}'
                index = SimpleNamespace(target=lambda _file, overwrite=False: (destination, False))
                download = SimpleNamespace(suggested_filename=f'Board{wrong_extension}', save_as=MagicMock())
                page = MagicMock()
                page.url = 'https://www.figma.com/file/key'
                page.goto.return_value = None
                page.expect_download.return_value.__enter__.return_value.value = download
                browser = Browser(Path(directory))
                browser.context = object()
                browser.page = page
                browser._save_local_copy = lambda: None
                file = {'key': 'key', 'name': 'Board', 'editorType': editor_type}

                with self.assertRaisesRegex(FigmaError, 'unexpected file'):
                    browser.download(file, index, lambda *_args: None)
                download.save_as.assert_not_called()
                self.assertFalse(destination.exists())

                download.suggested_filename = f'Board{extension.upper()}'
                download.save_as.side_effect = lambda path: Path(path).write_bytes(b'PK' + b'\x00' * 2048)
                result = browser.download(file, index, lambda *_args: None)
                self.assertEqual(result['status'], 'saved')
                self.assertTrue(destination.exists())

    def test_indexed_path_extension_must_match_editor_type(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'Board.fig'
            destination.write_bytes(b'PK' + b'\x00' * 2048)
            index = SimpleNamespace(target=lambda _file, overwrite=False: (destination, False))
            browser = Browser(Path(directory))
            file = {'key': 'key', 'name': 'Board', 'editorType': 'figjam'}

            with self.assertRaisesRegex(FigmaError, 'backup path has an unexpected file type'):
                browser.download(file, index, lambda *_args: None)

    def test_existing_native_file_rejects_error_responses(self):
        for editor_type, extension in (('figjam', '.jam'), ('slides', '.deck')):
            for payload in (b'<html>Access denied</html>', b'{"error":"Access denied"}'):
                with self.subTest(editor_type=editor_type, payload=payload[:1]), tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / f'Board{extension}'
                    destination.write_bytes(payload + b' ' * 2048)
                    index = SimpleNamespace(target=lambda _file, overwrite=False: (destination, False))
                    browser = Browser(Path(directory))
                    file = {'key': 'key', 'name': 'Board', 'editorType': editor_type}

                    with self.assertRaisesRegex(FigmaError, 'HTML/JSON error response'):
                        browser.download(file, index, lambda *_args: None)

                    destination.write_bytes(b'PK' + b'\x00' * 2048)
                    self.assertEqual(browser.download(file, index, lambda *_args: None)['status'], 'exists')

    def test_new_native_file_rejects_error_response_and_removes_partial(self):
        for editor_type, extension in (('figjam', '.jam'), ('slides', '.deck')):
            for payload in (b'<html>Access denied</html>', b'{"error":"Access denied"}'):
                with self.subTest(editor_type=editor_type, payload=payload[:1]), tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / f'Board{extension}'
                    index = SimpleNamespace(target=lambda _file, overwrite=False: (destination, False))
                    download = SimpleNamespace(
                        suggested_filename=destination.name,
                        save_as=lambda path: Path(path).write_bytes(payload + b' ' * 2048),
                    )
                    page = MagicMock()
                    page.url = 'https://www.figma.com/file/key'
                    page.goto.return_value = None
                    page.expect_download.return_value.__enter__.return_value.value = download
                    browser = Browser(Path(directory))
                    browser.context = object()
                    browser.page = page
                    browser._save_local_copy = lambda: None
                    file = {'key': 'key', 'name': 'Board', 'editorType': editor_type}

                    with self.assertRaisesRegex(FigmaError, 'HTML/JSON error response'):
                        browser.download(file, index, lambda *_args: None)

                    self.assertFalse(destination.exists())
                    self.assertFalse(destination.with_name(destination.name + '.partial').exists())


class OverwriteTransactionTests(unittest.TestCase):
    old_payload = b'PK' + b'old' * 1024
    new_payload = b'PK' + b'new' * 1024

    def prepare(self, directory, existing=True):
        destination = Path(directory) / 'Board.fig'
        if existing:
            destination.write_bytes(self.old_payload)
        owners = {'old': destination} if existing else {}

        def commit(file, path):
            self.assertEqual(path.read_bytes(), self.new_payload)
            owners.clear()
            owners[file['key']] = path

        index = SimpleNamespace(target=MagicMock(return_value=(destination, False)),
                                commit_overwrite=MagicMock(side_effect=commit))
        download = SimpleNamespace(suggested_filename='Board.fig', save_as=MagicMock(
            side_effect=lambda path: Path(path).write_bytes(self.new_payload)))
        page = MagicMock()
        page.url = 'https://www.figma.com/design/new'
        page.goto.return_value = None
        page.expect_download.return_value.__enter__.return_value.value = download
        browser = Browser(Path(directory))
        browser.context = object()
        browser.page = page
        browser._save_local_copy = lambda: None
        file = {'key': 'new', 'name': 'Board', 'editorType': 'figma'}
        return browser, file, index, download, destination, owners

    def assert_original_preserved(self, destination, owners):
        self.assertEqual(destination.read_bytes(), self.old_payload)
        self.assertEqual(owners, {'old': destination})
        self.assertEqual(list(destination.parent.iterdir()), [destination])

    def test_overwrite_downloads_then_commits_new_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, download, destination, owners = self.prepare(directory)
            result = browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assertEqual(result['status'], 'saved')
            self.assertEqual(destination.read_bytes(), self.new_payload)
            self.assertEqual(owners, {'new': destination})
            self.assertEqual(list(destination.parent.iterdir()), [destination])
            index.target.assert_called_once_with(file, overwrite=True)
            index.commit_overwrite.assert_called_once_with(file, destination)
            download.save_as.assert_called_once()

    def test_failed_save_preserves_original_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, download, destination, owners = self.prepare(directory)

            def interrupted(path):
                Path(path).write_bytes(b'partial')
                raise RuntimeError('download interrupted')

            download.save_as.side_effect = interrupted
            with self.assertRaisesRegex(RuntimeError, 'download interrupted'):
                browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assert_original_preserved(destination, owners)
            index.commit_overwrite.assert_not_called()

    def test_invalid_download_preserves_original_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, download, destination, owners = self.prepare(directory)
            download.save_as.side_effect = lambda path: Path(path).write_bytes(b'<html>denied</html>' + b' ' * 2048)
            with self.assertRaisesRegex(FigmaError, 'HTML/JSON error response'):
                browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assert_original_preserved(destination, owners)
            index.commit_overwrite.assert_not_called()

    def test_failed_replace_preserves_original_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, _download, destination, owners = self.prepare(directory)
            with patch.object(Path, 'replace', side_effect=PermissionError('destination locked')):
                with self.assertRaisesRegex(PermissionError, 'destination locked'):
                    browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assert_original_preserved(destination, owners)
            index.commit_overwrite.assert_not_called()

    def test_failed_index_commit_restores_original_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, _download, destination, owners = self.prepare(directory)
            index.commit_overwrite.side_effect = OSError('index disk full')
            with self.assertRaisesRegex(OSError, 'index disk full'):
                browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assert_original_preserved(destination, owners)
            index.commit_overwrite.assert_called_once_with(file, destination)

    def test_failed_index_commit_removes_new_unowned_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, _download, destination, owners = self.prepare(directory, existing=False)
            index.commit_overwrite.side_effect = OSError('index disk full')
            with self.assertRaisesRegex(OSError, 'index disk full'):
                browser.download(file, index, lambda *_args: None, overwrite=True)
            self.assertFalse(destination.exists())
            self.assertEqual(owners, {})
            self.assertEqual(list(destination.parent.iterdir()), [])

    def test_failed_rollback_keeps_recoverable_original_copy(self):
        original_replace = Path.replace

        def replace(path, destination):
            if path.suffix == '.rollback':
                raise PermissionError('restore locked')
            return original_replace(path, destination)

        with tempfile.TemporaryDirectory() as directory:
            browser, file, index, _download, destination, owners = self.prepare(directory)
            index.commit_overwrite.side_effect = OSError('index disk full')
            with patch.object(Path, 'replace', autospec=True, side_effect=replace):
                with self.assertRaisesRegex(FigmaError, 'Could not restore the original backup') as failure:
                    browser.download(file, index, lambda *_args: None, overwrite=True)
            copies = list(destination.parent.glob('*.rollback'))
            self.assertEqual(len(copies), 1)
            self.assertEqual(copies[0].read_bytes(), self.old_payload)
            self.assertIn(str(copies[0]), str(failure.exception))
            self.assertEqual(owners, {'old': destination})
            self.assertFalse(destination.with_name(destination.name + '.partial').exists())


if __name__ == '__main__':
    unittest.main()
