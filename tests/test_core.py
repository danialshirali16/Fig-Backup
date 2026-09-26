import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from figma_backup.core import ArchiveIndex, EditorTypeCache, FigmaClient, FigmaError, PreferencesStore, TokenStore, TreeArchiveIndex, clean_name, merge_teams, team_id_from_input


class Response:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body
        self.ok = 200 <= status < 300
        self.headers = {}

    def json(self):
        return self.body


class CoreTests(unittest.TestCase):
    def test_preferences_defaults_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PreferencesStore(Path(directory) / 'Fig Backup')
            self.assertEqual(store.load(), {'language': 'en', 'theme': 'system', 'onboarding_complete': False, 'setup_version': 0})
            self.assertEqual(store.save({'language': 'fa', 'theme': 'dark'})['onboarding_complete'], False)
            self.assertEqual(store.save({'onboarding_complete': True})['language'], 'fa')
            self.assertEqual(store.load()['setup_version'], 0)
            self.assertEqual(store.save({'setup_version': 2})['setup_version'], 2)
            with self.assertRaises(FigmaError):
                store.save({'theme': 'neon'})

    def test_app_local_token_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            support = Path(directory) / 'Fig Backup'
            store = TokenStore(support)
            self.assertIsNone(store.load())
            store.save(' figd_test ')
            self.assertEqual(TokenStore(support).load(), 'figd_test')
            if sys.platform != 'win32':  # POSIX permission bits are not enforced on Windows
                self.assertEqual(stat.S_IMODE(support.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(store.path.stat().st_mode), 0o600)
            store.clear()
            self.assertIsNone(store.load())

    def test_name_and_team_parsing(self):
        self.assertEqual(clean_name('  Test/A:B  '), 'Test_A_B')
        self.assertEqual(team_id_from_input('https://www.figma.com/team/1558645977231861977/abc'), '1558645977231861977')
        self.assertEqual(merge_teams([{'id': '1', 'name': '1'}], [{'id': '1', 'name': 'Danny'}]), [{'id': '1', 'name': 'Danny'}])

    def test_windows_reserved_stems_get_a_suffix(self):
        self.assertEqual(clean_name('CON'), 'CON_')
        self.assertEqual(clean_name('con.fig design'), 'con_.fig design')
        self.assertEqual(clean_name('LPT1'), 'LPT1_')
        self.assertEqual(clean_name('Console'), 'Console')
        self.assertEqual(clean_name('aux'), 'aux_')

    def test_team_avatar_survives_refresh_without_a_new_image(self):
        saved = [{'id': '1', 'name': 'Old name', 'avatar': 'data:image/png;base64,YQ=='}]
        refreshed = [{'id': '1', 'name': 'New name'}]
        self.assertEqual(merge_teams(saved, refreshed), [
            {'id': '1', 'name': 'New name', 'avatar': 'data:image/png;base64,YQ=='}
        ])

    def test_collision_names_and_existing_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'Downloads'
            downloads.mkdir()
            first = ArchiveIndex(root, downloads)
            p1, _ = first.target({'key': 'a', 'name': 'Same'})
            p2, _ = first.target({'key': 'b', 'name': 'Same'})
            self.assertEqual(p1.name, 'Same.fig')
            self.assertEqual(p2.name, 'Same(1).fig')
            self.assertEqual(ArchiveIndex(root, downloads).target({'key': 'a', 'name': 'Renamed'})[0], p1)
            self.assertEqual(json.loads((root / 'downloads.json').read_text())['files']['b'], 'Same(1).fig')

    def test_native_single_file_paths_survive_restart(self):
        for editor_type, extension in (('figjam', '.jam'), ('slides', '.deck')):
            with self.subTest(editor_type=editor_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                downloads = root / 'Downloads'
                downloads.mkdir()
                file = {'key': 'original', 'name': 'Same', 'editorType': editor_type}
                first, _ = ArchiveIndex(root, downloads).target(file)
                first.write_bytes(b'x' * 2048)

                restarted = ArchiveIndex(root, downloads)
                self.assertEqual(restarted.target(file)[0], first)
                other, _ = restarted.target({**file, 'key': 'other'})
                self.assertEqual(other.name, f'Same(1){extension}')

    def test_tree_archive_keeps_folders_and_collision_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / 'Downloads'
            store = root / 'Support'
            team = {'id': '10', 'name': 'Team'}
            first = {'id': '20', 'name': 'Folder'}
            second = {'id': '21', 'name': 'Folder'}
            child = {'id': '22', 'name': 'Child'}
            index = TreeArchiveIndex(team, store, downloads)
            index.prepare_folders([[first], [second], [first, child]])
            p1, _ = index.target({'key': 'a', 'name': 'Same', '_folder_path': [first]})
            p2, _ = index.target({'key': 'b', 'name': 'Same', '_folder_path': [first]})
            p3, _ = index.target({'key': 'c', 'name': 'Same', '_folder_path': [second]})
            self.assertEqual(p1.relative_to(downloads).as_posix(), 'Fig Backup/Team/Folder/Same.fig')
            self.assertEqual(p2.name, 'Same(1).fig')
            self.assertEqual(p3.relative_to(downloads).as_posix(), 'Fig Backup/Team/Folder(1)/Same.fig')
            self.assertTrue((downloads / 'Fig Backup/Team/Folder/Child').is_dir())
            again = TreeArchiveIndex(team, store, downloads)
            self.assertEqual(again.target({'key': 'a', 'name': 'Renamed', '_folder_path': [first]})[0], p1)

    def test_native_tree_file_paths_survive_restart(self):
        for editor_type, extension in (('figjam', '.jam'), ('slides', '.deck')):
            with self.subTest(editor_type=editor_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                downloads = root / 'Downloads'
                support = root / 'Support'
                team = {'id': '10', 'name': 'Team'}
                folder = {'id': '20', 'name': 'Folder'}
                file = {'key': 'original', 'name': 'Same', 'editorType': editor_type, '_folder_path': [folder]}
                first, _ = TreeArchiveIndex(team, support, downloads).target(file)
                first.write_bytes(b'x' * 2048)

                restarted = TreeArchiveIndex(team, support, downloads)
                self.assertEqual(restarted.target(file)[0], first)
                other, _ = restarted.target({**file, 'key': 'other'})
                self.assertEqual(other.name, f'Same(1){extension}')

    def test_legacy_fallback_and_451_subfolders(self):
        paths = []
        def get(url, **kwargs):
            path = url.removeprefix('https://api.figma.com')
            paths.append(path)
            responses = {
                '/v2/teams/10/folders': Response(403, {'message': 'forbidden'}),
                '/v1/teams/10/projects': Response(200, {'projects': [{'id': '20', 'name': 'Project'}]}),
                '/v1/projects/20/files': Response(200, {'files': [{'key': 'f1', 'name': 'Design'}]}),
            }
            return responses[path]
        client = FigmaClient('dummy', get)
        self.assertEqual(client.top_folders('10')[0]['name'], 'Project')
        self.assertEqual(client.folder_api, 'v1')
        self.assertEqual(client.all_files({'id': '20'})[0]['key'], 'f1')
        self.assertNotIn('/v2/folders/20/folders', paths)

        def get_451(url, **kwargs):
            path = url.removeprefix('https://api.figma.com')
            return Response(451, {'message': 'unavailable'}) if path.endswith('/folders') else Response(200, {'files': []})
        client = FigmaClient('dummy', get_451)
        self.assertEqual(client.subfolders('20'), [])
        self.assertIn('20', client.unavailable_subfolders)
        self.assertEqual(client.all_files({'id': '20'}), [])

    def test_api_errors(self):
        client = FigmaClient('dummy', lambda *_args, **_kwargs: Response(403, {'message': 'forbidden'}))
        with self.assertRaises(FigmaError) as raised:
            client.files('20')
        self.assertEqual(raised.exception.status, 403)

    def test_non_json_success_response(self):
        class BadResponse(Response):
            def json(self):
                raise ValueError('Expecting value: line 1 column 1 (char 0)')

        client = FigmaClient('dummy', lambda *_args, **_kwargs: BadResponse(200, None))
        with self.assertRaises(FigmaError) as raised:
            client.files('20')
        self.assertIn('non-JSON', str(raised.exception))
        self.assertEqual(raised.exception.status, 200)

    def test_recursive_files_deduplicate_keys(self):
        responses = {
            '/v2/folders/1/files': {'files': [{'key': 'a', 'name': 'A'}]},
            '/v2/folders/1/folders': {'folders': [{'id': '2', 'name': 'Child'}]},
            '/v2/folders/2/files': {'files': [{'key': 'a', 'name': 'A'}, {'key': 'b', 'name': 'B'}]},
            '/v2/folders/2/folders': {'folders': []},
        }
        client = FigmaClient('dummy', lambda url, **_kwargs: Response(200, responses[url.removeprefix('https://api.figma.com')]))
        self.assertEqual([file['key'] for file in client.all_files({'id': '1'})], ['a', 'b'])
        files, folders = client.walk_tree([{'id': '1', 'name': 'Root'}])
        self.assertEqual([file['key'] for file in files], ['a', 'b'])
        self.assertEqual([[folder['name'] for folder in path] for path in folders], [['Root'], ['Root', 'Child']])


class EditorTypeCacheTests(unittest.TestCase):
    def test_types_survive_a_new_client(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'editor-types.json'
            calls = []

            def get(url, **_kwargs):
                calls.append(url)
                return Response(200, {'file': {'editorType': 'figjam'}})

            first = FigmaClient('dummy', get, type_cache=EditorTypeCache(path))
            self.assertEqual(first.editor_type({'key': 'abc'}), 'figjam')
            first.flush_types()
            self.assertEqual(len(calls), 1)

            # A second launch must answer from disk, without touching the API.
            second = FigmaClient('dummy', get, type_cache=EditorTypeCache(path))
            self.assertEqual(second.editor_type({'key': 'abc'}), 'figjam')
            self.assertEqual(len(calls), 1, 'a known type must not be fetched again')

    def test_cached_types_are_applied_to_a_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EditorTypeCache(Path(directory) / 'editor-types.json')
            store.set('a', 'slides')
            client = FigmaClient('dummy', lambda *_a, **_k: Response(200, {}), type_cache=store)
            files = [{'key': 'a', 'name': 'A'}, {'key': 'b', 'name': 'B'}]
            client.apply_cached_types(files)
            self.assertEqual(files[0]['editorType'], 'slides')
            self.assertNotIn('editorType', files[1], 'an unknown key stays unresolved')

    def test_flush_is_a_no_op_without_new_types(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'editor-types.json'
            EditorTypeCache(path).flush()
            self.assertFalse(path.exists(), 'nothing learned, nothing written')

    def test_a_corrupt_cache_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'editor-types.json'
            path.write_text('{not json', encoding='utf-8')
            self.assertEqual(EditorTypeCache(path).types, {})
            path.write_text('{"types": {"a": 7, "": "x"}}', encoding='utf-8')
            self.assertEqual(EditorTypeCache(path).types, {})

    def test_the_cache_is_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EditorTypeCache(Path(directory) / 'editor-types.json')
            store.LIMIT = 3
            for index in range(10):
                store.set(f'k{index}', 'figma')
            store.flush()
            self.assertEqual(len(EditorTypeCache(store.path).types), 3)


if __name__ == '__main__':
    unittest.main()


class NetworkErrorTests(unittest.TestCase):
    """A dropped connection must become a readable FigmaError, not a raw
    requests exception that reaches the user as urllib3 internals."""

    def _client_raising(self, error, counter):
        def get(*_args, **_kwargs):
            counter.append(1)
            raise error
        return FigmaClient('dummy', get)

    def test_connection_error_becomes_a_readable_figma_error(self):
        counter = []
        client = self._client_raising(requests.ConnectionError("HTTPSConnectionPool(host='api.figma.com', port=443): Max retries exceeded"), counter)
        with self.assertRaises(FigmaError) as raised:
            client.files('20')
        message = str(raised.exception)
        self.assertIn('Could not reach Figma', message)
        self.assertNotIn('HTTPSConnectionPool', message, 'library internals must not reach the user')
        self.assertNotIn('api.figma.com', message)

    def test_read_timeout_is_wrapped_too(self):
        client = self._client_raising(requests.ReadTimeout('read timeout=30'), [])
        with self.assertRaises(FigmaError) as raised:
            client.files('20')
        self.assertIn('Could not reach Figma', str(raised.exception))

    def test_a_transient_drop_is_retried_and_can_succeed(self):
        calls = []

        def get(*_args, **_kwargs):
            calls.append(1)
            if len(calls) < 3:
                raise requests.ConnectionError('dropped')
            return Response(200, {'files': [{'key': 'a', 'name': 'A'}]})

        client = FigmaClient('dummy', get)
        with patch('figma_backup.core.time.sleep') as sleep:
            self.assertEqual(client.files('20'), [{'key': 'a', 'name': 'A'}])
        self.assertEqual(len(calls), 3, 'two retries before giving up')
        self.assertEqual(sleep.call_count, 2)

    def test_it_gives_up_quickly_rather_than_hammering(self):
        counter = []
        client = self._client_raising(requests.ConnectionError('down'), counter)
        with patch('figma_backup.core.time.sleep'):
            with self.assertRaises(FigmaError):
                client.files('20')
        self.assertEqual(len(counter), FigmaClient.NETWORK_ATTEMPTS,
                         'a dead connection must not be retried like a 5xx')

    def test_http_messages_no_longer_leak_the_endpoint(self):
        client = FigmaClient('dummy', lambda *_a, **_k: Response(403, {'message': 'Not authorized'}))
        with self.assertRaises(FigmaError) as raised:
            client.files('20')
        message = str(raised.exception)
        self.assertEqual(message, 'Figma refused the request (HTTP 403): Not authorized.')
        self.assertNotIn('/v2/folders', message)
        self.assertEqual(raised.exception.status, 403)


class StaleExtensionRepairTests(unittest.TestCase):
    """A recorded .fig for a FigJam/Slides file must be re-pointed, not raise.

    The real case: the flat index lives in the legacy "Figma Fig Downloader"
    folder and was written by an older build that named everything .fig. Because
    the entry survived every reload, Retry re-read the same wrong name and could
    never recover on its own.
    """

    def test_flat_index_repoints_a_figjam_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support, downloads = root / 'support', root / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'KEY123': '00 Figma Onboarding.fig'}}), encoding='utf-8')
            index = ArchiveIndex(support=support, downloads=downloads)
            destination, _ = index.target({'key': 'KEY123', 'name': '00 Figma Onboarding', 'editorType': 'figjam'})
            self.assertEqual(destination.name, '00 Figma Onboarding.jam')
            stored = json.loads((support / 'downloads.json').read_text(encoding='utf-8'))['files']['KEY123']
            self.assertEqual(stored, '00 Figma Onboarding.jam', 'the repair must be persisted')

    def test_slides_entry_repoints_to_deck(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support, downloads = root / 'support', root / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'KEY9': 'Untitled.fig'}}), encoding='utf-8')
            destination, _ = ArchiveIndex(support=support, downloads=downloads).target(
                {'key': 'KEY9', 'name': 'Untitled', 'editorType': 'slides'})
            self.assertEqual(destination.name, 'Untitled.deck')

    def test_the_repair_is_stable_across_repeated_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support, downloads = root / 'support', root / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'K': 'Board.fig'}}), encoding='utf-8')
            for _ in range(3):
                index = ArchiveIndex(support=support, downloads=downloads)
                destination, _ = index.target({'key': 'K', 'name': 'Board', 'editorType': 'figjam'})
                self.assertEqual(destination.name, 'Board.jam', 'a retry must not drift to Board(1).jam')

    def test_a_correctly_named_entry_is_left_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support, downloads = root / 'support', root / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'K': 'Board.jam'}}), encoding='utf-8')
            destination, _ = ArchiveIndex(support=support, downloads=downloads).target(
                {'key': 'K', 'name': 'Board', 'editorType': 'figjam'})
            self.assertEqual(destination.name, 'Board.jam')

    def test_the_repair_avoids_overwriting_an_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            support, downloads = root / 'support', root / 'Downloads'
            support.mkdir(); downloads.mkdir()
            (support / 'downloads.json').write_text(
                json.dumps({'version': 1, 'files': {'K': 'Board.fig'}}), encoding='utf-8')
            (downloads / 'Board.jam').write_bytes(b'PK\x03\x04' + b'0' * 2048)
            destination, _ = ArchiveIndex(support=support, downloads=downloads).target(
                {'key': 'K', 'name': 'Board', 'editorType': 'figjam'})
            self.assertNotEqual(destination.name, 'Board.jam', 'must not claim a name another file already holds')

    def test_tree_index_repoints_while_keeping_the_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, support = root / 'Downloads', root / 'Support'
            team = {'id': '10', 'name': 'Team'}
            folder = {'id': '20', 'name': 'Mobile'}
            file = {'key': 'K', 'name': 'Board', 'editorType': 'figjam', '_folder_path': [folder]}

            seeded, _ = TreeArchiveIndex(team, support, downloads).target(file)
            self.assertEqual(seeded.name, 'Board.jam')

            # Poison the stored entry the way an older build would have.
            paths = support / 'archives' / '10' / 'paths.json'
            body = json.loads(paths.read_text(encoding='utf-8'))
            body['files']['K'] = body['files']['K'].replace('.jam', '.fig')
            paths.write_text(json.dumps(body), encoding='utf-8')

            repaired, _ = TreeArchiveIndex(team, support, downloads).target(file)
            self.assertEqual(repaired.name, 'Board.jam')
            self.assertEqual(repaired.parent, seeded.parent, 'the folder must not change')
            stored = json.loads(paths.read_text(encoding='utf-8'))['files']['K']
            self.assertTrue(stored.endswith('Board.jam'), 'the repair must be persisted')
