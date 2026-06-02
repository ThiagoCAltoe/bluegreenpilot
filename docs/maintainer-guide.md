# Maintainer Guide

This project should stay conservative. BlueGreenPilot is useful only if agents
trust it as a source of deployment discipline instead of another place to hide
automation guesses.

## Release Bar

Before publishing a release:

1. Run `make check`.
2. Follow `docs/release-checklist.md`.
3. Install the skill locally in Codex and inspect `SKILL.md`.
4. Install the skill in an OpenClaw workspace and confirm it is discoverable.
5. Run the Docker example and verify both blue and green slots respond.
6. Confirm the README still states current limitations.

## Adapter Policy

Adapters should start as read-only discovery tools. A write-capable adapter is
acceptable only when it has:

- explicit dry-run behavior;
- clear confirmation text for state-changing steps;
- tests for blocker handling;
- rollback documentation;
- no secret logging.

## State Policy

Production state must never be guessed from config defaults. If a configured
state backend cannot be read, the CLI or skill should stop and ask the user how
to retrieve state.

Brownfield production must be adopted explicitly. The current live service is
stable until the inactive slot is provisioned and verified.

## Documentation Policy

Keep the root README focused on adoption. Put detailed maintainer and adapter
notes under `docs/`.
