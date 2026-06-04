# Changelog

## v2026.6.4 - Environment and Slot Model Clarification

- Clarified that environments such as `homolog` and `prod` are not blue-green
  slots.
- Added hard rules preventing agents from treating `homolog = green` or
  `prod = blue` unless the repository config explicitly defines that topology
  and the user confirms the risk.
- Updated brownfield adoption guidance to require an equivalent secondary
  production slot before production deploy/switch plans.

## v2026.6.1 - Initial Public Release

- Added the BlueGreenPilot CLI with `init`, `adopt-prod`, `validate`, `status`,
  and `plan`.
- Added the AgentSkills-compatible `bluegreenpilot` skill for Codex, OpenClaw,
  and other skill-loading agents.
- Added brownfield production adoption for applications that are already live.
- Added config and state JSON schemas.
- Added Docker blue-green and no-Docker script examples.
- Added CI, tests, issue templates, pull request template, security policy,
  contributor guidance, release checklist, and community growth plan.
