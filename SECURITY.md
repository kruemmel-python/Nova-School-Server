# Security Policy

## Supported Versions

Nova School Server is under active development. Security fixes are applied to the current `main` branch and to the latest published release line.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| `main` | Yes |
| Older releases | No |

## Reporting a Vulnerability

Please do not open public GitHub issues for security vulnerabilities.

Use one of these channels instead:

- GitHub Security Advisories for this repository, if enabled
- direct contact with the maintainer through the repository owner profile

Please include:

- a short description of the issue
- affected component or file
- impact and attack scenario
- reproduction steps or proof of concept
- environment details, including operating system and deployment mode

## Response Expectations

The project aims to:

- acknowledge a valid report as quickly as possible
- confirm whether the issue is reproducible
- coordinate a fix and release guidance
- credit responsible disclosure when appropriate

Response time depends on maintainer availability. High-risk issues affecting isolation, authentication, remote execution, or data exposure are prioritized.

## Scope

Security-sensitive areas include in particular:

- authentication and session handling
- permissions and role enforcement
- container and runner isolation
- remote worker dispatch and validation
- certificate, token, and secret handling
- upload, export, and share endpoints
- LM Studio or other AI provider integrations

## Deployment Guidance

For production-like school deployments:

- prefer container-backed execution over host-process fallback
- restrict network exposure to trusted internal networks
- use Linux-based workers or a Linux server for the most predictable container runtime behavior
- treat runtime data, databases, and exported artifacts as sensitive
- avoid publishing mirrored documentation packs that contain licensed or organization-specific material unless redistribution is allowed

## Out of Scope

The following are generally out of scope unless they enable a direct security impact:

- local development misconfiguration on non-production machines
- missing optional desktop features that do not weaken isolation
- documentation typos or UI wording issues without security consequences
