# Contributing

Thank you for contributing to Nova School Server.

This project combines classroom workflows, secure code execution, offline documentation, curriculum management, and administrative tooling. Changes should therefore be practical, reviewable, and safe for school deployments.

## Contribution Principles

- prefer small, reviewable pull requests
- keep behavior explicit and testable
- preserve secure defaults
- document user-visible or operational changes
- avoid introducing machine-specific paths or environment assumptions

## Development Setup

### Requirements

- Python 3.12
- Git
- optional Docker or Podman for container-backed execution tests

### Install

```bash
python -m pip install -r requirements.txt
```

### Run the Server

Windows:

```powershell
.\start_server.ps1
```

Linux/macOS:

```bash
./start_server.sh
```

## Running Tests

Windows:

```powershell
.\run_tests.ps1
```

Linux/macOS:

```bash
./run_tests.sh
```

Or directly:

```bash
python -m unittest
```

## Coding Guidelines

- use ASCII unless the file already relies on non-ASCII text
- keep patches focused on the task at hand
- prefer clear, explicit code over clever shortcuts
- add tests for new logic where practical
- update documentation when changing public behavior, release tooling, setup, or admin workflows

## Security and Runtime Expectations

- do not weaken runner isolation casually
- treat authentication, permissions, remote worker dispatch, and artifact handling as sensitive areas
- preserve least-privilege defaults
- avoid adding host-specific assumptions to the documentation or implementation

## Pull Request Checklist

Before opening a pull request, confirm:

- tests pass locally
- changed behavior is documented where needed
- no secrets, runtime databases, caches, or generated workspaces are included
- release-impacting changes are reflected in `README.md`, `CHANGELOG.md`, or both when appropriate

## Commit Style

There is no hard enforcement, but concise imperative commit messages are preferred, for example:

- `Add release notes generator`
- `Fix LM Studio URL normalization`
- `Enhance README with architecture visuals`

## Reporting Bugs and Ideas

- use the bug report template for defects
- use the feature request template for product or UX proposals
- use the security policy for vulnerabilities
