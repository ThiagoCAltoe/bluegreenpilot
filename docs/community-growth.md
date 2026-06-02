# Community Growth Plan

BlueGreenPilot should grow by being useful to developers who want agents near
deployment work but do not trust them to improvise production operations.

## Positioning

Lead with a concrete promise:

> Stop coding agents from guessing your blue-green deployment flow.

Avoid positioning it as a generic deployment tool. The strongest angle is
agent-safe release discipline: persistent config, persistent state, explicit
switch gates, and rollback-first planning.

## First Public Milestones

1. Publish `v0.1.0` with the Codex/OpenClaw skill, CLI, schemas, and Docker
   example.
2. Add a no-Docker/script deployment example.
3. Add a GitHub Actions example that validates BlueGreenPilot config on pull
   requests.
4. Record a short demo: configure a repo, plan prod deploy, block on unknown
   state, fix state, render safe plan.
5. Invite maintainers of small SaaS apps, agencies, and indie projects to test
   real deploy topologies.

## Contribution Themes

- Deployment variants: Docker, no-Docker, CI, nginx, Cloudflare, load balancer.
- State backends: repo, server file, CI artifact, object storage.
- Database policies: snapshot, mock, empty, manual, reversible migrations.
- Agent compatibility: Codex, OpenClaw, Claude Code, other AgentSkills loaders.
- Examples and runbooks from real projects.

## Launch Checklist

- README explains the problem in the first screen.
- Demo config works with `make check`.
- Skill installation instructions are tested.
- First release has clear limitations.
- Issues are pre-seeded with roadmap items.
- A pinned announcement shows one before/after deployment plan.

## Star Strategy

Focus on developers already experimenting with agents in real repos:

- Post a concise demo thread with the production switch gate as the hook.
- Share the Docker example and ask for unusual deployment variants.
- Write a short article: "How to keep coding agents from improvising deploys."
- Open issues for adapter ideas and invite contributors to own one.
- Keep the roadmap public and ship visible small releases weekly at first.
