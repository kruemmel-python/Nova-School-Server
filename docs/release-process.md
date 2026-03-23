# Release and Milestone Process

This document defines the lightweight release process for Nova School Server.

## Versioning

The project currently follows a pragmatic pre-1.0 release model:

- `v0.x.y`
- minor versions for meaningful feature increments
- patch versions for focused fixes and packaging improvements

Examples:

- `v0.1.0`
- `v0.2.0`
- `v0.2.1`

## Milestone Naming

Milestones should use release-oriented names:

- `v0.2.0 - Production hardening and Linux-first runtime`
- `v0.3.0 - Curriculum and classroom expansion`

Short names are acceptable when the scope is already obvious:

- `v0.2.0`

## Label Conventions

The repository uses labels in three groups:

### Type

- `bug`
- `enhancement`
- `documentation`

### Domain

- `security`
- `frontend`
- `runner`
- `curriculum`
- `offline-docs`
- `distributed-worker`
- `admin-ui`
- `ai-mentor`

### Delivery and Triage

- `priority:high`
- `release:blocker`
- `needs:repro`
- `good first issue`
- `help wanted`

The canonical label set is versioned in `.github/labels.json`.

## Issue Triage

When new issues arrive:

1. classify the issue type
2. add one or more domain labels
3. add `needs:repro` if the report is not yet actionable
4. assign `priority:high` or `release:blocker` only when justified
5. attach the issue to a version milestone if it belongs to a planned release

## Pull Requests

Pull requests should:

- reference the related issue or milestone when possible
- describe risk and validation clearly
- update documentation if public behavior changes
- avoid bundling unrelated work into one release candidate

## Release Preparation

Before publishing a release:

1. confirm milestone scope is complete
2. resolve or consciously defer `release:blocker` issues
3. run tests and relevant manual validation
4. update `CHANGELOG.md`
5. generate release notes from Git history
6. build and verify release assets
7. publish the GitHub release and attach assets

## Release Notes

Release notes are generated from the repository history with:

```bash
python -m nova_school_server.release_notes . --notes-tag v0.1.0 --notes-path ./release-notes-v0.1.0.md
```

The generated `CHANGELOG.md` should remain committed in the repository.
