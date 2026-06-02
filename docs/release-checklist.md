# Release Checklist

Use this before the first public release.

## Repository

1. Create the GitHub repository.
2. Update `pyproject.toml` with real `project.urls`.
3. Run `make check`.
4. Confirm `.github/workflows/ci.yml` passes on GitHub.
5. Confirm `.gitignore` excludes local generated files.

## Skill

1. Install `skills/bluegreenpilot` in Codex.
2. Ask Codex to configure a fresh test repository.
3. Confirm it creates `.bluegreenpilot/config.yaml`.
4. Confirm it refuses to switch production without explicit confirmation.
5. Install in an OpenClaw workspace and confirm it is listed.

## Documentation

1. Re-read the README from a new user's perspective.
2. Make sure limitations are still honest.
3. Add real screenshots or terminal examples only after they reflect the current
   release.
4. Add known issues if OpenClaw or Codex behavior diverges.

## Versioning

Use OpenClaw-style CalVer for public project releases:

```txt
YYYY.M.D
```

The first public release is `2026.6.1`, tagged as `v2026.6.1`. Keep the project
in alpha until:

- config/state schema changes are stable;
- at least two deployment variants are covered by examples;
- the skill has been tested in Codex and OpenClaw;
- contributors have a clear path for adapters and state backends.

Config files keep their own schema version:

```yaml
version: 1
```
