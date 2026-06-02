from __future__ import annotations

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTest(unittest.TestCase):
    def test_skill_frontmatter_is_agent_skills_compatible(self) -> None:
        text = (ROOT / "skills/bluegreenpilot/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))

        end = text.find("\n---\n", 4)
        self.assertNotEqual(end, -1)

        frontmatter = text[4:end].splitlines()
        values: dict[str, str] = {}
        for line in frontmatter:
            if not line.strip():
                continue
            self.assertNotIn("\n", line)
            key, sep, value = line.partition(":")
            self.assertEqual(sep, ":", line)
            values[key.strip()] = value.strip()

        self.assertEqual(values["name"], "bluegreenpilot")
        self.assertTrue(values["description"].strip('"'))
        self.assertIn("metadata", values)
        json.loads(values["metadata"])


if __name__ == "__main__":
    unittest.main()
