"""Conservative CLI for BlueGreenPilot.

The CLI validates and plans blue-green deployments. It intentionally does not
perform traffic switches, deploys, destructive cleanup, or database operations.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
import re
import sys


ROOT = Path(".bluegreenpilot")
VALID_SLOTS = {"blue", "green"}
VALID_SWITCH_METHODS = {"manual", "script", "nginx", "cloudflare", "load-balancer", "ci"}
VALID_ROLLBACK_METHODS = {"manual", "script", "ci"}
VALID_DATA_MODES = {"snapshot", "mock", "empty", "manual"}
VALID_MIGRATION_POLICIES = {"require_snapshot", "manual", "allow_safe_only"}
VALID_STATE_BACKENDS = {"repo", "server-file", "ci-artifact", "object-storage", "manual"}
VALID_INACTIVE_SLOT_STATUS = {"not-provisioned", "provisioned", "verified"}


CONFIG_TEMPLATE = """version: 1
app: CHANGE_ME
strategy: blue-green

branches:
  dev: dev
  homolog: homolog
  prod: main

environments:
  dev:
    deploy_mode: local
    strategy: single-slot
  homolog:
    deploy_mode: docker
    strategy: blue-green
    data_mode: snapshot
  prod:
    deploy_mode: docker
    strategy: blue-green

slots:
  homolog:
    blue_url: https://blue.homolog.example.com
    green_url: https://green.homolog.example.com
    public_url: https://homolog.example.com
  prod:
    blue_url: https://blue.example.com
    green_url: https://green.example.com
    public_url: https://example.com

database:
  homolog_data_mode: snapshot # snapshot | mock | empty | manual
  prod_snapshot_required: true
  migration_policy: require_snapshot # require_snapshot | manual | allow_safe_only

state:
  backend: repo # repo | server-file | ci-artifact | object-storage | manual
  path: .bluegreenpilot/state.{environment}.yaml

checks:
  healthcheck_path: /health
  smoke_commands:
    - npm run build
    - npm test

switch:
  method: manual # manual | script | nginx | cloudflare | load-balancer | ci
  command: ""

rollback:
  method: manual # manual | script | ci
  command: ""
"""


STATE_TEMPLATE = """version: 1
environment: {env}
active_slot: UNKNOWN
inactive_slot: UNKNOWN
last_successful_release: ""
last_switch_at: ""
last_snapshot: ""
"""


def _opposite_slot(slot: str) -> str:
    return "green" if slot == "blue" else "blue"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _clean_scalar(value: str) -> str:
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def _extract_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.*?)\s*$", text)
    if not match:
        return ""
    return _clean_scalar(match.group(1))


def _extract_section(text: str, section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = text.splitlines()
    in_section = False
    section_indent = 0

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped == f"{section}:":
            in_section = True
            section_indent = indent
            continue

        if in_section and indent <= section_indent and not stripped.startswith("-"):
            break

        if in_section:
            match = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
            if match:
                values[match.group(1)] = _clean_scalar(match.group(2))

    return values


def _extract_section_scalar(text: str, section: str, key: str) -> str:
    return _extract_section(text, section).get(key, "")


def _extract_list(text: str, key: str) -> list[str]:
    values: list[str] = []
    lines = text.splitlines()
    in_list = False
    key_indent = 0

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped == f"{key}:":
            in_list = True
            key_indent = indent
            continue

        if in_list and indent <= key_indent and not stripped.startswith("-"):
            break

        if in_list and stripped.startswith("-"):
            values.append(_clean_scalar(stripped[1:].strip()))

    return values


def _extract_named_block(text: str, section: str, name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = text.splitlines()
    in_section = False
    in_block = False
    section_indent = 0
    block_indent = 0

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped == f"{section}:":
            in_section = True
            section_indent = indent
            continue

        if in_section and indent <= section_indent and not stripped.startswith("-"):
            break

        if in_section and stripped == f"{name}:":
            in_block = True
            block_indent = indent
            continue

        if in_block and indent <= block_indent and not stripped.startswith("-"):
            break

        if in_block:
            match = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.*?)\s*$", line)
            if match:
                values[match.group(1)] = _clean_scalar(match.group(2))

    return values


def _database_mode_for_env(config: str, env: str) -> str:
    env_config = _extract_named_block(config, "environments", env)
    if env_config.get("data_mode"):
        return env_config["data_mode"]

    if env == "prod":
        snapshot_required = _extract_section_scalar(config, "database", "prod_snapshot_required")
        if snapshot_required.lower() == "true":
            return "snapshot-required"
        if snapshot_required.lower() == "false":
            return "manual"

    return _extract_section_scalar(config, "database", "homolog_data_mode") or "manual"


def _state_path(env: str) -> Path:
    return ROOT / f"state.{env}.yaml"


def _load_config() -> tuple[Path, str]:
    path = ROOT / "config.yaml"
    return path, _read(path)


def _load_state(env: str) -> tuple[Path, str]:
    path = _state_path(env)
    return path, _read(path)


def _validate_config(config: str) -> list[str]:
    findings: list[str] = []

    app = _extract_scalar(config, "app")
    if not app or app == "CHANGE_ME":
        findings.append("FAIL config.app is missing or still CHANGE_ME")

    strategy = _extract_scalar(config, "strategy")
    if strategy not in {"blue-green", "single-slot", ""}:
        findings.append(f"FAIL config.strategy has unsupported value: {strategy}")

    switch = _extract_section_scalar(config, "switch", "method")
    if not switch:
        findings.append("FAIL switch.method is missing")
    elif switch not in VALID_SWITCH_METHODS:
        findings.append(f"FAIL switch.method is unsupported: {switch}")

    rollback = _extract_section_scalar(config, "rollback", "method")
    if not rollback:
        findings.append("FAIL rollback.method is missing")
    elif rollback not in VALID_ROLLBACK_METHODS:
        findings.append(f"FAIL rollback.method is unsupported: {rollback}")

    healthcheck = _extract_scalar(config, "healthcheck_path")
    if not healthcheck:
        findings.append("WARN checks.healthcheck_path is missing")

    data_mode = _extract_section_scalar(config, "database", "homolog_data_mode")
    if data_mode and data_mode not in VALID_DATA_MODES:
        findings.append(f"WARN database.homolog_data_mode is unsupported: {data_mode}")

    migration_policy = _extract_section_scalar(config, "database", "migration_policy")
    if migration_policy and migration_policy not in VALID_MIGRATION_POLICIES:
        findings.append(f"WARN database.migration_policy is unsupported: {migration_policy}")

    state_backend = _extract_section_scalar(config, "state", "backend")
    if not state_backend:
        findings.append("FAIL state.backend is missing; Codex may not know where runtime state persists")
    elif state_backend not in VALID_STATE_BACKENDS:
        findings.append(f"FAIL state.backend is unsupported: {state_backend}")

    adoption = _extract_section(config, "adoption")
    adoption_mode = adoption.get("mode")
    if adoption_mode and adoption_mode != "brownfield":
        findings.append(f"FAIL adoption.mode is unsupported: {adoption_mode}")

    inactive_status = adoption.get("inactive_slot_status")
    if inactive_status and inactive_status not in VALID_INACTIVE_SLOT_STATUS:
        findings.append(f"FAIL adoption.inactive_slot_status is unsupported: {inactive_status}")

    return findings


def _validate_state(env: str, state: str) -> list[str]:
    findings: list[str] = []

    if not state:
        return [f"FAIL state for {env} is missing"]

    recorded_env = _extract_scalar(state, "environment")
    if recorded_env and recorded_env != env:
        findings.append(f"FAIL state.{env}.environment is {recorded_env}")

    active = _extract_scalar(state, "active_slot")
    inactive = _extract_scalar(state, "inactive_slot")

    if not active or active == "UNKNOWN":
        findings.append(f"FAIL state.{env}.active_slot is unknown")
    elif active not in VALID_SLOTS:
        findings.append(f"FAIL state.{env}.active_slot must be blue or green")

    if not inactive or inactive == "UNKNOWN":
        findings.append(f"FAIL state.{env}.inactive_slot is unknown")
    elif inactive not in VALID_SLOTS:
        findings.append(f"FAIL state.{env}.inactive_slot must be blue or green")

    if active in VALID_SLOTS and inactive in VALID_SLOTS and active == inactive:
        findings.append(f"FAIL state.{env} active_slot and inactive_slot are the same")

    release = _extract_scalar(state, "last_successful_release")
    if not release:
        findings.append(f"WARN state.{env}.last_successful_release is empty")

    inactive_status = _extract_scalar(state, "inactive_slot_status")
    if inactive_status and inactive_status not in VALID_INACTIVE_SLOT_STATUS:
        findings.append(f"FAIL state.{env}.inactive_slot_status is unsupported: {inactive_status}")

    return findings


def _has_fail(findings: list[str]) -> bool:
    return any(item.startswith("FAIL") for item in findings)


def cmd_init(_: argparse.Namespace) -> int:
    ROOT.mkdir(exist_ok=True)
    (ROOT / "history").mkdir(exist_ok=True)

    config = ROOT / "config.yaml"
    if not config.exists():
        config.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        print(f"created {config}")
    else:
        print(f"exists  {config}")

    for env in ("dev", "homolog", "prod"):
        state = _state_path(env)
        if not state.exists():
            state.write_text(STATE_TEMPLATE.format(env=env), encoding="utf-8")
            print(f"created {state}")
        else:
            print(f"exists  {state}")

    print("next: edit .bluegreenpilot/config.yaml and replace UNKNOWN state values")
    return 0


def cmd_adopt_prod(args: argparse.Namespace) -> int:
    if args.active_slot not in VALID_SLOTS:
        print("FAIL --active-slot must be blue or green")
        return 2

    if args.state_backend not in VALID_STATE_BACKENDS:
        print(f"FAIL --state-backend is unsupported: {args.state_backend}")
        return 2

    inactive = _opposite_slot(args.active_slot)
    blue_url = args.public_url if args.active_slot == "blue" else "TO_BE_PROVISIONED"
    green_url = args.public_url if args.active_slot == "green" else "TO_BE_PROVISIONED"

    ROOT.mkdir(exist_ok=True)
    (ROOT / "history").mkdir(exist_ok=True)

    config_path = ROOT / "config.yaml"
    state_path = _state_path("prod")

    if (config_path.exists() or state_path.exists()) and not args.force:
        print("FAIL .bluegreenpilot config/state already exists; pass --force to overwrite")
        return 2

    config = f"""version: 1
app: {args.app}
strategy: blue-green

branches:
  prod: {args.source}

environments:
  prod:
    deploy_mode: {args.deploy_mode}
    strategy: blue-green

slots:
  prod:
    blue_url: {blue_url}
    green_url: {green_url}
    public_url: {args.public_url}

database:
  homolog_data_mode: manual
  prod_snapshot_required: true
  migration_policy: require_snapshot

state:
  backend: {args.state_backend}
  path: {args.state_path}

adoption:
  mode: brownfield
  current_prod_slot: {args.active_slot}
  inactive_slot_status: not-provisioned

checks:
  healthcheck_path: {args.healthcheck_path}
  smoke_commands: []

switch:
  method: {args.switch_method}
  command: ""

rollback:
  method: {args.rollback_method}
  command: ""
"""
    state = f"""version: 1
environment: prod
active_slot: {args.active_slot}
inactive_slot: {inactive}
last_successful_release: {args.source}
last_switch_at: ""
last_snapshot: ""
adoption_status: brownfield
inactive_slot_status: not-provisioned
"""

    config_path.write_text(config, encoding="utf-8")
    state_path.write_text(state, encoding="utf-8")

    print(f"created {config_path}")
    print(f"created {state_path}")
    print(f"production mapped as stable {args.active_slot}; {inactive} must be provisioned before switch")
    print("next: create an exact inactive slot clone, verify it, then set adoption.inactive_slot_status to provisioned or verified")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    _, config = _load_config()
    if not config:
        print("FAIL .bluegreenpilot/config.yaml is missing")
        return 2

    findings = _validate_config(config)

    envs = args.env or ["prod"]
    for env in envs:
        _, state = _load_state(env)
        findings.extend(_validate_state(env, state))

    if not findings:
        print("OK BlueGreenPilot configuration is valid for requested environment(s)")
        return 0

    for item in findings:
        print(item)

    return 1 if _has_fail(findings) else 0


def cmd_status(args: argparse.Namespace) -> int:
    _, config = _load_config()
    if not config:
        print("missing .bluegreenpilot/config.yaml; run init first", file=sys.stderr)
        return 2

    state_path, state = _load_state(args.env)
    if not state:
        print(f"missing {state_path}; create or retrieve environment state", file=sys.stderr)
        return 2

    active = _extract_scalar(state, "active_slot") or "UNKNOWN"
    inactive = _extract_scalar(state, "inactive_slot") or "UNKNOWN"
    inactive_status = _extract_scalar(state, "inactive_slot_status") or ""
    release = _extract_scalar(state, "last_successful_release") or ""
    switch = _extract_section_scalar(config, "switch", "method") or "UNKNOWN"
    rollback = _extract_section_scalar(config, "rollback", "method") or "UNKNOWN"
    state_backend = _extract_section_scalar(config, "state", "backend") or "UNKNOWN"

    print(f"environment: {args.env}")
    print(f"active_slot: {active}")
    print(f"inactive_slot: {inactive}")
    if inactive_status:
        print(f"inactive_slot_status: {inactive_status}")
    print(f"last_successful_release: {release or '(none recorded)'}")
    print(f"state_backend: {state_backend}")
    print(f"switch_method: {switch}")
    print(f"rollback_method: {rollback}")

    blockers = _validate_state(args.env, state)
    hard_blockers = [item for item in blockers if item.startswith("FAIL")]
    if hard_blockers:
        print("blockers:")
        for item in hard_blockers:
            print(f"- {item[5:]}")
        return 1

    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    _, config = _load_config()
    if not config:
        print("missing .bluegreenpilot/config.yaml; run init first", file=sys.stderr)
        return 2

    _, state = _load_state(args.env)
    active = _extract_scalar(state, "active_slot") or "UNKNOWN"
    inactive = _extract_scalar(state, "inactive_slot") or "UNKNOWN"
    health = _extract_scalar(config, "healthcheck_path") or "/health"
    env_config = _extract_named_block(config, "environments", args.env)
    deploy_mode = env_config.get("deploy_mode") or "UNKNOWN"
    switch = _extract_section_scalar(config, "switch", "method") or "manual"
    switch_command = _extract_section_scalar(config, "switch", "command")
    rollback = _extract_section_scalar(config, "rollback", "method") or "manual"
    rollback_command = _extract_section_scalar(config, "rollback", "command")
    data_mode = _database_mode_for_env(config, args.env)
    migration_policy = _extract_section_scalar(config, "database", "migration_policy") or "manual"
    state_backend = _extract_section_scalar(config, "state", "backend") or "manual"
    adoption = _extract_section(config, "adoption")
    inactive_slot_status = adoption.get("inactive_slot_status") or _extract_scalar(state, "inactive_slot_status")
    smoke_commands = _extract_list(config, "smoke_commands")
    stamp = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    print(f"BlueGreenPilot deploy plan ({stamp})")
    print(f"Target: {args.env}")
    print(f"Current active slot: {active}")
    print(f"Deploy target: {inactive}")
    print(f"Source: {args.source or '(confirm branch/tag/commit)'}")
    print(f"Deploy mode: {deploy_mode}")
    print(f"Healthcheck: {health}")
    if smoke_commands:
        print("Smoke commands:")
        for command in smoke_commands:
            print(f"- {command}")
    else:
        print("Smoke commands: (none configured)")
    print(f"Database data mode: {data_mode}")
    print(f"Migration policy: {migration_policy}")
    print(f"State backend: {state_backend}")
    if adoption.get("mode"):
        print(f"Adoption mode: {adoption.get('mode')}")
    if inactive_slot_status:
        print(f"Inactive slot status: {inactive_slot_status}")
    print(f"Switch method: {switch}")
    if switch_command:
        print(f"Switch command: {switch_command}")
    print(f"Rollback method: {rollback}")
    if rollback_command:
        print(f"Rollback command: {rollback_command}")
    print("")
    print("Required gates:")
    print("1. Confirm source branch/tag/commit.")
    print("2. Confirm database snapshot/migration policy.")
    print("3. Deploy only to the inactive slot.")
    print("4. Run healthcheck and smoke commands.")
    if args.env == "prod":
        print("5. Request explicit final confirmation before production switch.")
    else:
        print("5. Ask before switching target environment traffic.")
    print("6. Switch traffic and record state/history.")

    findings = _validate_config(config) + _validate_state(args.env, state)
    if args.env == "prod" and inactive_slot_status == "not-provisioned":
        findings.append("FAIL adoption inactive slot is not provisioned; do not deploy or switch production yet")

    hard_blockers = [item for item in findings if item.startswith("FAIL")]
    if hard_blockers:
        print("")
        print("BLOCKERS:")
        for item in hard_blockers:
            print(f"- {item[5:]}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    global ROOT

    parser = argparse.ArgumentParser(prog="bluegreenpilot")
    parser.add_argument(
        "--project",
        default=".",
        help="target application directory that contains .bluegreenpilot",
    )
    sub = parser.add_subparsers(required=True)

    init = sub.add_parser("init", help="create .bluegreenpilot templates")
    init.set_defaults(func=cmd_init)

    adopt = sub.add_parser("adopt-prod", help="create a safe brownfield production adoption config")
    adopt.add_argument("--app", required=True, help="application name")
    adopt.add_argument("--public-url", required=True, help="current production URL")
    adopt.add_argument(
        "--deploy-mode",
        default="manual",
        choices=["docker", "no-docker", "mixed", "script", "manual", "ci"],
        help="how production is currently deployed",
    )
    adopt.add_argument("--active-slot", default="blue", choices=["blue", "green"])
    adopt.add_argument("--source", default="CURRENT_PRODUCTION", help="current production branch, tag, commit, or release label")
    adopt.add_argument("--state-backend", default="manual", choices=sorted(VALID_STATE_BACKENDS))
    adopt.add_argument("--state-path", default=".bluegreenpilot/state.{environment}.yaml")
    adopt.add_argument("--healthcheck-path", default="/health")
    adopt.add_argument("--switch-method", default="manual", choices=sorted(VALID_SWITCH_METHODS))
    adopt.add_argument("--rollback-method", default="manual", choices=sorted(VALID_ROLLBACK_METHODS))
    adopt.add_argument("--force", action="store_true", help="overwrite existing .bluegreenpilot config/state")
    adopt.set_defaults(func=cmd_adopt_prod)

    validate = sub.add_parser("validate", help="validate config and state")
    validate.add_argument("--env", action="append", help="environment to validate")
    validate.set_defaults(func=cmd_validate)

    status = sub.add_parser("status", help="show environment state")
    status.add_argument("env", nargs="?", default="prod")
    status.set_defaults(func=cmd_status)

    plan = sub.add_parser("plan", help="render a safe deployment plan")
    plan.add_argument("env", nargs="?", default="prod")
    plan.add_argument("--source", help="branch, tag, or commit to deploy")
    plan.set_defaults(func=cmd_plan)

    args = parser.parse_args(argv)
    ROOT = Path(args.project) / ".bluegreenpilot"
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
