# Maintenance & Operations

Security isn't a one-time check at a single commit. This is how the project is meant
to stay secure over time: how fast things get fixed, when the base image is refreshed,
what to do if a secret leaks, and how problems surface even when nobody is pushing.

## Fix timelines by severity

When a scanner (or Dependabot) flags something, the target windows for acting on it:

| Severity | What to do | Target |
|----------|------------|--------|
| **Critical** | Fix or mitigate right away; do not release until it's cleared | 24-48 hours |
| **High** | Prioritise over normal feature work | Within 1 week |
| **Medium** | Schedule into the normal backlog | Within 1 month |
| **Low / unfixable** | Track it; clear it opportunistically (e.g. at the next base-image refresh) | Best effort |

The gates enforce the top of this table at build time: high and critical findings
fail the build, medium only warns. See [GATE_POLICY.md](GATE_POLICY.md) for the details.

## Base-image refresh

The container inherits CVEs from its base image (`python:3.12-slim`). Most of the
findings that remain after remediation live in that OS layer, and many have no fix
available yet (which is why the image gate uses `--ignore-unfixed`). Policy:

- Rebuild on the latest `python:3.12-slim` regularly (monthly), and sooner when a
  relevant base-image CVE gets a fix.
- The weekly scheduled scan (below) is what tells you a refresh is worth doing, by
  surfacing newly published base-image CVEs.
- For stricter control, the base image can be pinned by digest for reproducibility
  (a possible future improvement).

## If a secret leaks

If a real credential is ever committed:

1. **Rotate and revoke it immediately.** Treat it as compromised the moment it lands
   in git, even in a private repo.
2. **Remove it from the code** and load it from an environment variable or a secrets
   manager instead.
3. **Acknowledge the historical copy.** Gitleaks scans the full history, so the leak
   stays visible in old commits. Rewriting history is usually impractical, so add the
   finding's fingerprint to `.gitleaksignore` once the key has been rotated.
4. **Check for exposure** (access logs, usage of the leaked key).

The `remediated` branch shows steps 2 and 3 for the seeded fake AWS key.

## Automated dependency updates (Dependabot)

[`.github/dependabot.yml`](.github/dependabot.yml) has Dependabot open weekly pull
requests for outdated or vulnerable pip packages and GitHub Actions. This is the
routine way fixes come in, and it pairs with Trivy: Trivy detects vulnerable
dependencies during the pipeline, Dependabot proposes the upgrade as a ready-to-merge
PR. Review and merge them according to the severity timelines above.

## Scheduled re-scan

The pipeline runs on a weekly schedule (Mondays, 06:00 UTC) as well as on every push
and pull request. That way a CVE published against a dependency or the base image gets
caught on the timer, even if nobody has touched the repo. Each scheduled run also
appends a row to `metrics.csv`, so that file doubles as a findings-over-time log: you
can watch the findings count drift as new CVEs appear without any code change.

## Where to look

- **Current findings:** the repo's Security tab (Code scanning), fed by SARIF from
  every scanner.
- **Trend over time:** `metrics.csv` on the [`metrics`](../../tree/metrics) branch.
