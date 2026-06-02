# Contributing

BlueGreenPilot is a deployment safety project. Contributions should make agent
behavior more predictable, auditable, and conservative.

## Good First Contributions

- Add real-world configuration examples.
- Improve validation messages.
- Add adapters for non-destructive discovery.
- Document rollback and database edge cases.
- Test the skill with Codex, OpenClaw, and other AgentSkills-compatible systems.

## Safety Rules

- Do not add commands that switch production traffic without confirmation.
- Do not add secret storage to `.bluegreenpilot/config.yaml`.
- Do not make production state guessable from defaults.
- Do not hide deploy blockers behind warnings.

## Local Validation

```bash
python -m bluegreenpilot --help
python -m bluegreenpilot validate --env prod
python -m bluegreenpilot --project examples/node-docker-bluegreen validate --env homolog --env prod
python -m json.tool schemas/config.schema.json
python -m json.tool schemas/state.schema.json
```
