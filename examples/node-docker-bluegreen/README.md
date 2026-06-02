# Node Docker Blue-Green Example

This example shows a small app with two Docker slots and a repo-local
BlueGreenPilot configuration.

It is intentionally simple:

- `blue` listens on `http://localhost:8081`
- `green` listens on `http://localhost:8082`
- the public switch is modeled as `manual`
- homolog data mode is `mock`
- production state is recorded in `.bluegreenpilot/state.prod.yaml`

From the repository root:

```bash
python -m bluegreenpilot validate --env homolog --env prod
python -m bluegreenpilot status prod
python -m bluegreenpilot plan prod --source main
```

From this example directory:

```bash
docker compose up --build
```

BlueGreenPilot will not switch traffic by itself. It renders the safe plan,
checks known blockers, and requires explicit confirmation before production
switch steps.
