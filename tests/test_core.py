import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from figma_backup.core import ArchiveIndex, FigmaClient, FigmaError, PreferencesStore, TokenStore, TreeArchiveIndex, clean_name, merge_teams, team_id_from_input


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
            self.assertEqual(store.load(), {'language': 'en', 'theme': 'system', 'onboarding_complete': False})
            self.assertEqual(store.save({'language': 'fa', 'theme': 'dark'})['onboarding_complete'], False)
            self.assertEqual(store.save({'onboarding_complete': True})['language'], 'fa')
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


if __name__ == '__main__':
    unittest.main()
