---
updated_at: 2026-07-13T12:14:21+07:00
---

# Tracked git hooks

This directory is version-controlled so the repo's git hooks travel with the clone.
The active hook here is `post-commit`, which refreshes the local **GitNexus** index
(`gitnexus analyze`) in the background after each commit.

## One-time activation (required per clone)

Git never auto-applies a repo-provided hooks path (by design), so each fresh clone
must point git at this directory once:

```sh
git config core.hooksPath .githooks
```

That's it — the hook then runs on every commit. It no-ops unless the repo has a
`.gitnexus/` index, runs `gitnexus analyze` detached so it never blocks the commit,
and uses a `flock` single-flight lock so overlapping commits can't corrupt the index.
Logs go to `.gitnexus/analyze.log`.
