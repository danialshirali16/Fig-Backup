import base64
import unittest
from types import SimpleNamespace

from figma_backup.browser import Browser


class AvatarTests(unittest.TestCase):
    def test_figma_avatar_is_embedded_for_the_app(self):
        calls = []

        class Response:
            ok = True
            headers = {'content-type': 'image/png', 'content-length': '3'}

            def body(self):
                return b'PNG'

        browser = Browser()
        browser.context = SimpleNamespace(request=SimpleNamespace(
            get=lambda url, **kwargs: (calls.append(url), Response())[1]
        ))
        teams = browser._hydrate_avatars([
            {'id': '1', 'name': 'Design', 'avatar': 'https://s3-alpha.figma.com/team.png'}
        ], [])
        self.assertEqual(teams[0]['avatar'], 'data:image/png;base64,' + base64.b64encode(b'PNG').decode())
        self.assertEqual(calls, ['https://s3-alpha.figma.com/team.png'])

    def test_untrusted_avatar_url_uses_saved_image(self):
        browser = Browser()
        browser.context = SimpleNamespace(request=SimpleNamespace(
            get=lambda *_args, **_kwargs: self.fail('unexpected request')
        ))
        saved = [{'id': '1', 'name': 'Design', 'avatar': 'data:image/png;base64,UE5H'}]
        teams = browser._hydrate_avatars([
            {'id': '1', 'name': 'Design', 'avatar': 'https://elsewhere.example/avatar.png'}
        ], saved)
        self.assertEqual(teams[0]['avatar'], saved[0]['avatar'])


if __name__ == '__main__':
    unittest.main()
