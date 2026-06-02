from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bluegreenpilot import cli


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


class BlueGreenPilotCliTest(unittest.TestCase):
    def test_init_creates_config_state_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, stderr = run_cli("--project", tmp, "init")

            self.assertEqual(code, 0, stderr)
            self.assertIn("created", stdout)
            self.assertTrue((Path(tmp) / ".bluegreenpilot/config.yaml").exists())
            self.assertTrue((Path(tmp) / ".bluegreenpilot/history").is_dir())

            config = (Path(tmp) / ".bluegreenpilot/config.yaml").read_text(encoding="utf-8")
            self.assertIn("state:", config)
            self.assertIn("backend: repo", config)

    def test_validate_blocks_unknown_production_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli("--project", tmp, "init")

            config = Path(tmp) / ".bluegreenpilot/config.yaml"
            config.write_text(
                config.read_text(encoding="utf-8").replace("app: CHANGE_ME", "app: demo"),
                encoding="utf-8",
            )

            code, stdout, _ = run_cli("--project", tmp, "validate", "--env", "prod")

            self.assertEqual(code, 1)
            self.assertIn("FAIL state.prod.active_slot is unknown", stdout)
            self.assertIn("FAIL state.prod.inactive_slot is unknown", stdout)

    def test_example_config_validates(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/node-docker-bluegreen"),
            "validate",
            "--env",
            "homolog",
            "--env",
            "prod",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("OK BlueGreenPilot configuration is valid", stdout)

    def test_prod_plan_uses_snapshot_required_policy(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/node-docker-bluegreen"),
            "plan",
            "prod",
            "--source",
            "main",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Target: prod", stdout)
        self.assertIn("Deploy target: green", stdout)
        self.assertIn("Deploy mode: docker", stdout)
        self.assertIn("- node --check app/index.js", stdout)
        self.assertIn("Database data mode: snapshot-required", stdout)
        self.assertIn("Request explicit final confirmation before production switch", stdout)

    def test_homolog_plan_uses_homolog_data_mode(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/node-docker-bluegreen"),
            "plan",
            "homolog",
            "--source",
            "homolog",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Target: homolog", stdout)
        self.assertIn("Database data mode: mock", stdout)
        self.assertIn("Ask before switching target environment traffic", stdout)

    def test_status_reports_state_backend(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/node-docker-bluegreen"),
            "status",
            "prod",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("state_backend: repo", stdout)
        self.assertIn("active_slot: blue", stdout)

    def test_no_docker_script_example_validates(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/no-docker-script"),
            "validate",
            "--env",
            "homolog",
            "--env",
            "prod",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("OK BlueGreenPilot configuration is valid", stdout)

    def test_no_docker_script_plan_shows_script_commands(self) -> None:
        code, stdout, stderr = run_cli(
            "--project",
            str(ROOT / "examples/no-docker-script"),
            "plan",
            "prod",
            "--source",
            "main",
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("Deploy mode: script", stdout)
        self.assertIn("State backend: server-file", stdout)
        self.assertIn("Switch command: ./scripts/switch-to-{slot}.sh", stdout)
        self.assertIn("Rollback command: ./scripts/switch-to-{slot}.sh", stdout)

    def test_adopt_prod_marks_existing_production_as_brownfield(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, stderr = run_cli(
                "--project",
                tmp,
                "adopt-prod",
                "--app",
                "existing-app",
                "--public-url",
                "https://example.com",
                "--deploy-mode",
                "script",
                "--active-slot",
                "blue",
                "--source",
                "prod-current",
                "--state-backend",
                "manual",
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("production mapped as stable blue", stdout)

            state = (Path(tmp) / ".bluegreenpilot/state.prod.yaml").read_text(encoding="utf-8")
            self.assertIn("active_slot: blue", state)
            self.assertIn("inactive_slot_status: not-provisioned", state)

            code, plan, _ = run_cli("--project", tmp, "plan", "prod", "--source", "main")

            self.assertEqual(code, 1)
            self.assertIn("Adoption mode: brownfield", plan)
            self.assertIn("Inactive slot status: not-provisioned", plan)
            self.assertIn("adoption inactive slot is not provisioned", plan)

    def test_skill_helper_supports_brownfield_adoption(self) -> None:
        script = ROOT / "skills/bluegreenpilot/scripts/bluegreenpilot.py"
        with tempfile.TemporaryDirectory() as tmp:
            adopt = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "adopt-prod",
                    "--app",
                    "existing-app",
                    "--public-url",
                    "https://example.com",
                    "--active-slot",
                    "green",
                    "--source",
                    "prod-current",
                ],
                cwd=tmp,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(adopt.returncode, 0, adopt.stderr)
            self.assertIn("production mapped as stable green", adopt.stdout)

            plan = subprocess.run(
                [sys.executable, str(script), "plan", "--env", "prod"],
                cwd=tmp,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(plan.returncode, 1)
            self.assertIn("Inactive slot status: not-provisioned", plan.stdout)
            self.assertIn("adoption inactive slot is not provisioned", plan.stdout)


if __name__ == "__main__":
    unittest.main()
