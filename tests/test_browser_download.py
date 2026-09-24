import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

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
                index = SimpleNamespace(target=lambda _file: (destination, False))
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
            index = SimpleNamespace(target=lambda _file: (destination, False))
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
                    index = SimpleNamespace(target=lambda _file: (destination, False))
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
                    index = SimpleNamespace(target=lambda _file: (destination, False))
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


if __name__ == '__main__':
    unittest.main()
