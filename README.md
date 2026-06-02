# BlueGreenPilot

BlueGreenPilot is a deployment safety protocol for coding agents.

It helps Codex, OpenClaw, Claude Code, and other AgentSkills-compatible systems
plan blue-green releases without relying on chat memory, improvised production
steps, or guessed runtime state.

Before production traffic can move, the agent must know the topology, read the
current environment state, identify the active slot, deploy only to the inactive
slot, verify it, ask for explicit final confirmation, and record what changed.

BlueGreenPilot is not a magic deploy button. It is a guardrail layer for teams
that want agents involved in release work without letting them invent the
release process.

## What Ships

- An AgentSkills-compatible skill at `skills/bluegreenpilot/SKILL.md`.
- A no-dependency Python CLI for init, validation, status, and deploy planning.
- JSON schemas for config and environment state.
- A Docker blue-green example with persistent `.bluegreenpilot` files.
- A no-Docker script-based blue-green example.
- References for Docker, no-Docker, mixed, database, and state workflows.
- Tests, CI, and maintainer/release checklists.

## Why

Real deployment environments rarely look the same:

- Docker may exist in production, homolog, both, or neither.
- Branches may be `dev`, `homolog`, and `prod`, or a single trunk.
- Switches may happen through nginx, Cloudflare, CI, load balancers, scripts, or
  manual runbooks.
- Homolog may need production snapshots, mock data, empty data, or manual data.
- Production rollback may be a traffic switch, a script, or a documented human
  procedure.

BlueGreenPilot gives agents a durable operating model in the repository so they
can preserve these decisions across machines, sessions, CI, homolog, and
production.

## Core Rules

- Do not store secrets in BlueGreenPilot config or state.
- Do not guess the active production slot.
- Do not deploy to the active slot in a blue-green environment.
- Do not switch production traffic without explicit final confirmation.
- Do not proceed with risky database changes without a snapshot or documented
  migration policy.
- Do not claim a manual switch happened until the user confirms it.
- Record release, slot, verification, rollback, and history metadata after
  switches or rollbacks.

## Quick Start

Inside the application repository you want to configure:

```bash
python -m bluegreenpilot --help
python -m bluegreenpilot init
python -m bluegreenpilot validate --env prod
python -m bluegreenpilot status prod
python -m bluegreenpilot plan prod --source main
```

The CLI is conservative. It creates templates, validates known blockers, and
prints a safe plan. It does not switch traffic, deploy, delete containers,
modify databases, or run destructive infrastructure commands.

## Existing Production

For an application that is already live, start with brownfield adoption instead
of a normal deploy plan:

```bash
python -m bluegreenpilot adopt-prod \
  --app my-app \
  --public-url https://example.com \
  --deploy-mode script \
  --active-slot blue \
  --source CURRENT_PRODUCTION \
  --state-backend manual
```

This records the current production service as the stable active slot and marks
the inactive slot as `not-provisioned`. BlueGreenPilot must then block normal
production deploy/switch plans until the secondary slot exists and has been
verified.

The CLI and skill do not guess whether a project is already in production. They
use explicit user input plus read-only discovery. If `.bluegreenpilot` is
missing and the user asks about deploys, the skill must ask whether production
already exists before creating a plan.

See `docs/brownfield-adoption.md` for the full adoption flow.

## Skill Installation

Codex-style local install:

```bash
mkdir -p ~/.codex/skills
cp -R skills/bluegreenpilot ~/.codex/skills/bluegreenpilot
```

OpenClaw workspace install:

```bash
mkdir -p ./skills
cp -R skills/bluegreenpilot ./skills/bluegreenpilot
openclaw skills list
```

When the skill is active, ask the agent to use BlueGreenPilot before deployment
work:

```txt
Use BlueGreenPilot to configure this repository for homolog and production
blue-green deploys.
```

## Config and State

BlueGreenPilot uses repository config plus environment state:

```txt
.bluegreenpilot/
  config.yaml
  state.dev.yaml
  state.homolog.yaml
  state.prod.yaml
  history/
```

`config.yaml` is versioned. It describes topology, branches, environments,
deploy modes, slots, checks, database policy, switch method, rollback method,
and where runtime state persists.

`state.<environment>.yaml` records what is true right now: active slot,
inactive slot, last release, last switch, and last snapshot. For production,
state can live in the repo, on the server, in CI artifacts, in object storage,
or another trusted backend. The `state.backend` field tells the agent where to
look so it does not forget production reality after moving from dev to homolog
or prod.

Example config:

```yaml
version: 1
app: my-app
strategy: blue-green

branches:
  dev: dev
  homolog: homolog
  prod: main

environments:
  homolog:
    deploy_mode: docker
    strategy: blue-green
    data_mode: snapshot
  prod:
    deploy_mode: docker
    strategy: blue-green

slots:
  prod:
    blue_url: https://blue.example.com
    green_url: https://green.example.com
    public_url: https://example.com

database:
  homolog_data_mode: snapshot
  prod_snapshot_required: true
  migration_policy: require_snapshot

state:
  backend: ci-artifact
  path: bluegreenpilot/state.{environment}.yaml

checks:
  healthcheck_path: /health
  smoke_commands:
    - npm run build
    - npm test

switch:
  method: manual
  command: ""

rollback:
  method: manual
  command: ""
```

Example state:

```yaml
version: 1
environment: prod
active_slot: blue
inactive_slot: green
last_successful_release: abc1234
last_switch_at: 2026-06-01T12:00:00Z
last_snapshot: prod-2026-06-01T113000Z.sql
```

## Example

The `examples/node-docker-bluegreen` project demonstrates two Docker slots and
repo-local BlueGreenPilot state.

```bash
cd examples/node-docker-bluegreen
docker compose up --build
```

From the repository root:

```bash
python -m bluegreenpilot --project examples/node-docker-bluegreen validate --env homolog --env prod
python -m bluegreenpilot --project examples/node-docker-bluegreen status prod
python -m bluegreenpilot --project examples/node-docker-bluegreen plan prod --source main
```

The `examples/no-docker-script` project demonstrates a script-based deployment
with server-file state:

```bash
python -m bluegreenpilot --project examples/no-docker-script validate --env homolog --env prod
python -m bluegreenpilot --project examples/no-docker-script plan prod --source main
```

## Agent Workflow

When asked to deploy, promote, switch, roll back, or configure release flow, the
agent should:

1. Read `.bluegreenpilot/config.yaml`.
2. Identify the target environment.
3. Read or retrieve `state.<environment>.yaml`.
4. Confirm active and inactive slots.
5. Generate a deploy plan with blockers.
6. Deploy only to the inactive slot.
7. Run configured health and smoke checks.
8. Ask for explicit final confirmation before production switch.
9. Switch traffic only after confirmation.
10. Record state, history, release id, rollback metadata, and verification
    result.

The agent must stop when production state, rollback, health checks, or database
policy are unknown.

## Compatibility

BlueGreenPilot is built around the portable `SKILL.md` shape used by
AgentSkills-style systems.

- Codex: supported through `SKILL.md` and `agents/openai.yaml`.
- OpenClaw: designed for OpenClaw's AgentSkills-compatible loader.
- Other agents: usable when they can load skill-style Markdown instructions.

Current status: tested locally as a Codex-style skill and CLI package; designed
for OpenClaw compatibility, with more ecosystem testing planned.

## Roadmap

- Stronger YAML and JSON Schema validation.
- GitHub Action for deploy-plan verification.
- State backend adapters for CI artifacts and object storage.
- Read-only discovery adapters for Docker, nginx, Cloudflare, and CI.
- Release history recorder.
- More examples for no-Docker, mixed Docker, and branch promotion workflows.

## Contributing

Run the local quality gate before opening a pull request:

```bash
make check
```

See `CONTRIBUTING.md`, `docs/maintainer-guide.md`, and
`docs/release-checklist.md` for project standards. See
`docs/community-growth.md` for the public launch and adoption plan.

## License

MIT
