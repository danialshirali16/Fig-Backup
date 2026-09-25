"""Keep the UI and backend version strings in lockstep."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionSyncTest(unittest.TestCase):
    def test_package_json_matches_bridge_version(self):
        package_version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
        bridge_source = (ROOT / "figma_backup" / "app.py").read_text(encoding="utf-8")
        match = re.search(r'"version":\s*"([^"]+)"', bridge_source)
        self.assertIsNotNone(match, "bootstrap() no longer reports a version string")
        self.assertEqual(package_version, match.group(1))


if __name__ == "__main__":
    unittest.main()
