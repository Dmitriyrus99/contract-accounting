# .agents/skills

This folder is the canonical install target for Codex-installed local skills.

Install command:

```
npx skills add ./agent-skills -a codex --copy -y
```

The active source of truth is `./agent-skills` and the following folders:

- `ferum-grill-with-docs`
- `ferum-domain-modeling`
- `ferum-tdd`
- `ferum-diagnosing-bugs`
- `ferum-codebase-design`
- `ferum-code-review`
- `ferum-architecture-survey`

Do not edit copies in `.agents/skills` directly.
