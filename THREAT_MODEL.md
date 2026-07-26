# Threat Model

A lightweight threat model for the demo app. This is the design-phase step: thinking
about what could go wrong before leaning on tools to catch it. It lists the app's
assets and entry points, maps each threat to the OWASP Top 10 (2021), and notes which
pipeline stage should catch it (and which threats no tool can).

## Scope and assets

The app is a small Flask + SQLite service (a login and a per-user item list). The
things worth protecting:

| Asset | Why it matters |
|-------|----------------|
| User credentials (`users` table) | Account takeover if they leak or get bypassed |
| Per-user item data (`items.owner`) | One user shouldn't see another's data |
| Session secret (`SECRET_KEY`) | Sessions can be forged if it's predictable or leaks |
| Cloud credentials / S3 bucket (modelled in Terraform) | Data exposure if the bucket is public or keys leak |
| The CI/CD pipeline and repo | Supply-chain integrity of what ships |

## Actors and trust boundaries

- **Anonymous internet user:** can reach `/login` and the public `/search`.
- **Authenticated user** (`alice`, `bob`): should see only their own data.
- **Attacker:** crafts malicious input or links, and can read the public repo.

Data crosses a few trust boundaries: between the browser and Flask (over HTTP),
between the app and SQLite, between the app and the (hypothetical) AWS S3 bucket, and
between a developer, the Git repo, and the CI pipeline.

## Entry points

| Entry point | Auth | Untrusted input |
|-------------|------|-----------------|
| `POST /login` | none | `username`, `password` |
| `GET /search` | none | `q` query parameter |
| `GET /items` | session | (session cookie) |
| `GET /logout` | session | none |

## Threats, OWASP Top 10, and what catches them

Each threat, its OWASP 2021 category, the seeded vulnerability that stands in for it,
and the stage expected to catch it:

| Threat | OWASP 2021 | Seeded | Caught by |
|--------|-----------|--------|-----------|
| SQL injection via the login form | **A03: Injection** | #1 | CodeQL (SAST) and ZAP (DAST) |
| Reflected XSS via `/search` | **A03: Injection** | #6 | CodeQL (SAST) and ZAP (DAST) |
| Hardcoded cloud credential in source | **A07: Identification & Auth Failures** (CWE-798) | #2 | Gitleaks |
| Vulnerable or outdated dependency | **A06: Vulnerable & Outdated Components** | #3 | Trivy (SCA + image) |
| Public S3 bucket / infra misconfig | **A05: Security Misconfiguration** | #4 | Checkov (IaC) |
| Flask debug mode enabled | **A05: Security Misconfiguration** | (bonus) | CodeQL |
| Broken access control (cross-user data) | **A01: Broken Access Control** | #5 | nobody (see below) |

## What the scanners cover, and what needs a human

The pipeline covers whole classes of technical vulnerability cheaply and on every push:
injection, leaked secrets, vulnerable components, and misconfiguration. These are
pattern- or signature-based, which is exactly what scanners are good at.

What it doesn't cover is business-logic and authorization flaws. Seeded vuln **#5**
(any logged-in user can read another user's items) is a real, high-impact case of
**A01: Broken Access Control**, yet no scanner flags it. The code is "valid," and no
tool knows what the app is *supposed* to allow. Catching it takes a human doing an
authorization review or threat model, and the fix is to scope the query to the
logged-in owner.

So the takeaway: automated scanning is necessary but not enough. A fully green
pipeline can still ship a serious flaw. Design-phase threat modeling and human review
still matter. The tools handle breadth and repetition; people handle intent.
