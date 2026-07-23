# Gate Policy

The rule is simple: the pipeline **fails the build on high or critical findings**, and
just **warns on medium** (they get reported, but don't block). That's what turns the
scanners from passive checkers into a gate that can actually stop a build.

## From report-only to enforced

Each security stage was first added in **report-only** mode (findings printed, build
stayed green) so we could wire it in and confirm it worked. Step 7 then switched the
serious findings to **enforced**: a non-zero exit turns the check red, which blocks
the merge once branch protection is on. The value of report-only first: you can prove a stage
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

Commit `ci: enforce gate policy …` (and others after it, which can be observed in commit history) produced **4 green, 3 red** — the red checks are
the gates correctly blocking the seeded high/critical vulnerabilities:
https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672

<img width="645" height="358" alt="image" src="https://github.com/user-attachments/assets/4c38f2d2-4d66-4deb-bc0a-fc0e4ff7467e" />

- ❌ Secret Scan (Gitleaks) — `leaks found: 1` - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347524
- ❌ SCA & Image Scan (Trivy) — `urllib3` HIGH: 6 - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347606
- ❌ IaC Scan (Checkov) — `CKV_AWS_53/54/55/56` failed (hard-fail) - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347555
- ✅ SAST (CodeQL), DAST (ZAP), Lint & Test, Validate (Terraform)

A red build here is a **good** sign: the pipeline spotted the planted vulnerabilities
and blocked them. Fixing a vulnerability turns its stage green again. That's exactly
what the `remediated` branch shows: with all of them fixed, the whole pipeline passes.

## Making the gates un-bypassable (branch protection)

Failing checks only *prevent a merge* if the branch is **protected**. Without
protection, a red pipeline is advisory — someone could still push straight to `main`.
The recommended `main` configuration (GitHub → Settings → Branches → branch
protection rule, or a Ruleset):

- **Require a pull request before merging** — no direct pushes to `main`.
- **Require status checks to pass**, with *"require branches to be up to date"*, and
  mark these gating jobs as **required**:
  - `Lint & Test (Python)`
  - `Validate (Terraform)`
  - `Secret Scan (Gitleaks)`
  - `SCA & Image Scan (Trivy)`
  - `IaC Scan (Checkov)`
- **Require the CodeQL code-scanning check** (and/or "no new high-severity alerts").
  This is *how CodeQL enforces* — it doesn't fail the workflow step; instead branch
  protection blocks the merge on its code-scanning results.
- **Do not allow bypassing** the above — include administrators.

With these rules plus the security-gated `publish` job, insecure code can neither
**merge** (branch protection) nor **deploy** (gated publish).

> **Note for this demo repo:** `main` intentionally carries the seeded
> vulnerabilities, so its checks are red. Enabling "require status checks" would —
> correctly — block every merge, which is exactly the point but would halt
> development on this teaching repo. So the configuration is **documented here rather
> than enforced**. In a real project you would turn it on; the seeded vulns would be
> fixed on a branch and merged only once green.
>
> CodeQL/ZAP are **report-only** (they publish to the Security tab but don't fail the
> workflow), so they are not listed as required *build* checks — CodeQL is enforced
> via the code-scanning branch-protection check above instead.
