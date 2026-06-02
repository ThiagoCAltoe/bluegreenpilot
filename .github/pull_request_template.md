## Summary

What changed?

## Safety Review

- [ ] Does not store or print secrets.
- [ ] Does not switch production traffic without explicit confirmation.
- [ ] Does not guess production state.
- [ ] Handles blockers as failures when production safety depends on them.
- [ ] Adds or updates tests when behavior changes.

## Validation

```bash
make check
```
