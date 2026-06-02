from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

import bluegreenpilot


ROOT = Path(__file__).resolve().parents[1]


class VersioningTest(unittest.TestCase):
    def test_package_version_matches_project_metadata(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(bluegreenpilot.__version__, pyproject["project"]["version"])


if __name__ == "__main__":
    unittest.main()
