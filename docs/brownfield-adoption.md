# Brownfield Adoption

Use this workflow when an application is already serving production traffic
before BlueGreenPilot is introduced.

## Principle

BlueGreenPilot must not guess production state. Existing production is adopted
from explicit user input plus read-only discovery.

The current production service becomes the stable active slot. The opposite
slot is treated as missing until it is intentionally provisioned, checked, and
recorded.

## CLI Flow

```bash
python -m bluegreenpilot adopt-prod \
  --app my-app \
  --public-url https://example.com \
  --deploy-mode script \
  --active-slot blue \
  --source CURRENT_PRODUCTION \
  --state-backend manual
```

This creates:

```txt
.bluegreenpilot/config.yaml
.bluegreenpilot/state.prod.yaml
.bluegreenpilot/history/
```

The generated state records:

```yaml
active_slot: blue
inactive_slot: green
adoption_status: brownfield
inactive_slot_status: not-provisioned
```

## Required Next Steps

1. Provision the inactive slot as an exact production-compatible clone.
2. Confirm healthcheck and smoke commands.
3. Confirm database snapshot/migration policy.
4. Update `adoption.inactive_slot_status` to `provisioned`.
5. Deploy candidate release to the inactive slot.
6. Verify the inactive slot.
7. Update `adoption.inactive_slot_status` to `verified`.
8. Only then plan a production switch.

## Agent Behavior

When `.bluegreenpilot` is missing and the user asks about production deploys,
the agent should ask whether production already exists. If yes, use brownfield
adoption before any deploy plan.

When `adoption.mode: brownfield` and `inactive_slot_status: not-provisioned`,
the agent must stop and explain that blue-green deployment cannot start until
the secondary slot is provisioned.
