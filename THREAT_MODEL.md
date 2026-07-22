# Threat Model

A lightweight threat model for the demo app — the **design-phase** activity of
identifying what could go wrong *before* relying on tools to catch it. It maps the
app's assets and entry points to concrete threats, aligns each to the **OWASP
Top 10 (2021)**, and records which pipeline stage is expected to detect it (and
which threats no tool can catch).

## Scope & assets

The app is a minimal Flask + SQLite service (login + per-user item list). The assets
worth protecting:

| Asset | Why it matters |
|-------|----------------|
| User credentials (`users` table) | Account takeover if leaked/bypassed |
| Per-user item data (`items.owner`) | Confidentiality between users |
| Session secret (`SECRET_KEY`) | Forged sessions if predictable/leaked |
| Cloud credentials / S3 bucket (modelled in Terraform) | Data exposure if the bucket is public or keys leak |
| The CI/CD pipeline & repo | Supply-chain integrity of what ships |

## Actors & trust boundaries

- **Anonymous internet user** — can reach `/login` and the public `/search`.
- **Authenticated user** (`alice`, `bob`) — should see only *their own* data.
- **Attacker** — crafts malicious input/links, inspects the public repo.

Trust boundaries crossed by data:
`browser ⇄ Flask (HTTP)` · `app ⇄ SQLite` · `app ⇄ (hypothetical) AWS S3` ·
`developer ⇄ Git repo ⇄ CI pipeline`.

## Entry points

| Entry point | Auth | Untrusted input |
|-------------|------|-----------------|
| `POST /login` | none | `username`, `password` |
| `GET /search` | none | `q` query parameter |
| `GET /items` | session | (session cookie) |
| `GET /logout` | session | — |

## Threats → OWASP Top 10 → control

Each identified threat, the OWASP 2021 category, the seeded vulnerability that
represents it, and the pipeline stage expected to catch it:

| Threat | OWASP 2021 | Seeded | Detected by |
|--------|-----------|--------|-------------|
| SQL injection via login form | **A03: Injection** | #1 | CodeQL (SAST) + ZAP (DAST) |
| Reflected XSS via `/search` | **A03: Injection** | #6 | CodeQL (SAST) + ZAP (DAST) |
| Hardcoded cloud credential in source | **A07: Identification & Auth Failures** (CWE-798) | #2 | Gitleaks |
| Vulnerable/outdated dependency | **A06: Vulnerable & Outdated Components** | #3 | Trivy (SCA + image) |
| Public S3 bucket / infra misconfig | **A05: Security Misconfiguration** | #4 | Checkov (IaC) |
| Flask debug mode enabled | **A05: Security Misconfiguration** | (bonus) | CodeQL |
| Broken access control (cross-user data) | **A01: Broken Access Control** | #5 | **none — see below** |

## What automated scanning covers vs. what needs humans

The pipeline covers whole *classes* of technical vulnerability cheaply and on every
push: injection, leaked secrets, vulnerable components, and misconfiguration. These
are pattern- or signature-detectable, which is exactly what scanners excel at.

**What it does not cover:** business-logic and authorization flaws. Seeded vuln **#5**
(any logged-in user can read another user's items) is a real, high-impact **A01:
Broken Access Control** issue, yet *no* scanner flags it — the code is "valid," and no
tool knows the app's *intended* authorization rules. It requires a human doing
authorization review / threat modeling to spot, and the fix is to scope the query to
the current owner.

**Conclusion:** automated scanning is necessary but **not sufficient**. A fully green
pipeline can still ship a serious flaw. Design-phase threat modeling and human review
remain essential — the tools handle breadth and repetition; humans handle intent.
