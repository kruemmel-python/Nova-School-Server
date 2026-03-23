# Nova School Server Roadmap

This roadmap describes the current public direction of the project. It is intentionally practical and grouped by product outcome rather than by internal module only.

## Near-Term Focus

### 1. Linux-first runtime stability

Goal:

- make Linux-based execution the most predictable and production-ready deployment path

Key outcomes:

- stronger worker-first execution model
- improved runtime health checks
- clearer server diagnostics for Docker, Podman, and worker availability
- better deployment guidance for Ubuntu-based school servers

### 2. Classroom-ready curriculum expansion

Goal:

- turn Nova School Server into a structured learning platform, not only an execution environment

Key outcomes:

- more built-in courses beyond Python, C++, and Java
- stronger teacher tooling for assessment review
- better certificate verification and course branding
- reusable curriculum authoring patterns for schools

### 3. Documentation and offline knowledge quality

Goal:

- provide high-quality offline learning material without requiring direct client web access

Key outcomes:

- improve mirrored reference coverage and search relevance
- strengthen product and role-based documentation
- refine import and maintenance workflows for official or primary references

## Mid-Term Focus

### 4. Linux server deployment package

Goal:

- make a pure Linux server deployment the preferred operational model

Key outcomes:

- hardened server setup guidance
- better packaging for school IT teams
- cleaner separation between central server and worker execution

### 5. Advanced classroom collaboration

Goal:

- improve real-time collaboration, moderation, and review in large class settings

Key outcomes:

- richer notebook collaboration behavior
- stronger teacher moderation workflows
- improved chat and project-room controls
- clearer review and audit analytics

## Long-Term Direction

### 6. Stronger isolation and controlled network egress

Goal:

- keep raising the security baseline for school deployments

Key outcomes:

- better runtime hardening profiles
- stronger proxy- and worker-based execution models
- reduced dependence on weaker local fallback modes

### 7. School-scale operability

Goal:

- support repeated deployment and maintenance in real institutions

Key outcomes:

- better release hygiene
- clearer upgrade guidance
- reproducible packaging and operational documentation
- maintainable repository standards

## Milestone Strategy

The project uses version milestones for release planning, for example:

- `v0.2.0`
- `v0.3.0`

Each milestone should represent a coherent delivery step with a small number of clear outcomes, not a broad backlog bucket.

## How to Use This Roadmap

- use milestones for concrete release scope
- use labels for component and priority classification
- update this roadmap when strategic direction changes meaningfully
- keep detailed feature discussion in issues and pull requests
