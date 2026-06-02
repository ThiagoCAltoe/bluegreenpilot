# No-Docker Script Example

This example models a blue-green deployment where the application is deployed
by scripts instead of Docker.

The app itself is not included. The important part is the persisted deployment
contract:

- homolog uses mock data;
- production requires a database snapshot before risky migrations;
- switching and rollback are script-based;
- production state records the active slot and last successful release.

From the repository root:

```bash
python -m bluegreenpilot --project examples/no-docker-script validate --env homolog --env prod
python -m bluegreenpilot --project examples/no-docker-script plan prod --source main
```

An agent using BlueGreenPilot should inspect `scripts/deploy-green.sh` and
`scripts/switch-to-green.sh` only after producing a plan and asking before
state-changing actions.
