## Summary

<!-- 1-3 bullets describing what this PR does -->

- 

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Documentation
- [ ] Tests

## OI API compatibility

- [ ] No public API changed (internal only)
- [ ] New params added (backward-compatible defaults)
- [ ] Breaking change — documented in PR description

## Test plan

- [ ] `pytest tests/ -v` passes locally
- [ ] `ruff check . --select E,F,W --ignore E501` passes
- [ ] Tested manually with `pillai run` or `pillai "<task>"`

## Checklist

- [ ] No secrets or API keys committed
- [ ] No changes to `main` branch directly (use a feature branch)
- [ ] `safe_mode` warnings preserved for desktop/shell tools
- [ ] `skills.md` changes tested with semantic dedup
- [ ] Licensing: local free mode still works without a key
