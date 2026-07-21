# Gate Policy

**Policy:** the pipeline **fails the build on high/critical findings** and **warns
(reports without failing) on medium**. This is what turns the scanners from passive
observers into an enforced quality gate.

## Report-only → enforced

Each security stage was first added in **report-only** mode (findings printed, build
stayed green) so the stage could be wired in and validated. Step 7 flipped the
serious findings to **enforced** (non-zero exit → red check → blocked merge once
branch protection is on). The value of report-only first: you can prove a stage
*works* before you let it *block*.

## How each tool expresses severity (and how we gate it)

Each scanner models "severity" differently, so the policy is applied per tool:

| Stage | Severity model | Gate implementation | Behavior on the seeded vulns |
|-------|----------------|---------------------|------------------------------|
| **Gitleaks** (secrets) | A secret is a secret | `gitleaks detect` over full history, `--exit-code 1` | **Fails** — seeded AWS key found in history |
| **Trivy** (SCA + image) | Native LOW/MED/HIGH/CRIT | `--severity HIGH,CRITICAL --exit-code 1`; separate `MEDIUM --exit-code 0` pass to warn; image scan adds `--ignore-unfixed` | **Fails** — `urllib3` 6 HIGH CVEs |
| **Checkov** (IaC) | No CVSS — pass/fail per policy | `--soft-fail` (warn on all) **+** `--hard-fail-on CKV_AWS_53,54,55,56` (gate the serious ones) | **Fails** — public-access checks; the 6 best-practice gaps stay warnings |
| **CodeQL** (SAST) | Alerts in the Security tab | Does not fail the workflow step; enforced via **branch protection** (required "Code scanning" check) — see future work | Reports `py/sql-injection` (High) as an alert |
| **ZAP** (DAST) | Risk High/Med/Low/Info | Report-only; app's findings are Low/Med (headers) → per "warn on medium" it does not block | Warns (missing security headers) |

Key nuance for pass/fail tools (Checkov): with no CVSS, **the team defines severity
by choosing which checks gate** (`--hard-fail-on`). "Warn on medium" becomes "warn
on the checks we didn't hard-fail."

The `--ignore-unfixed` on the Trivy image scan is deliberate: the base image carries
many CVEs with no available fix. Gating on those would break the build permanently
for issues no one can act on, so only *fixable* HIGH/CRITICAL vulnerabilities gate.

## Verified enforcement run

Commit `ci: enforce gate policy …` produced **4 green, 3 red** — the red checks are
the gates correctly blocking the seeded high/critical vulnerabilities:
https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672

<img width="645" height="358" alt="image" src="https://github.com/user-attachments/assets/4c38f2d2-4d66-4deb-bc0a-fc0e4ff7467e" />

- ❌ Secret Scan (Gitleaks) — `leaks found: 1` - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347524
- ❌ SCA & Image Scan (Trivy) — `urllib3` HIGH: 6 - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347606
- ❌ IaC Scan (Checkov) — `CKV_AWS_53/54/55/56` failed (hard-fail) - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347555
- ✅ SAST (CodeQL), DAST (ZAP), Lint & Test, Validate (Terraform)

A red build here is **success**: the pipeline detected and blocked the planted
vulnerabilities. Removing/remediating a vuln returns its stage to green — the
detection → fix → verified-clean loop.

<!-- Add screenshots: (1) the report-only run (green with findings) vs (2) this
enforced run (red, blocked) for the before/after. -->
