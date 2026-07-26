# Gate Policy

The rule is simple: the pipeline **fails the build on high or critical findings**, and
just **warns on medium** (they get reported, but don't block). That's what turns the
scanners from passive checkers into a gate that can actually stop a build.

## From report-only to enforced

Each security stage was added in **report-only** mode first (findings printed, build
stayed green) so we could wire it in and confirm it worked. Step 7 then switched the
serious findings to **enforced**: a non-zero exit turns the check red, which blocks
the merge once branch protection is on. Doing report-only first means you can prove a
stage works before you let it block anything.

## How each tool handles severity (and how we gate it)

Each scanner thinks about "severity" a bit differently, so the policy is applied per tool:

| Stage | How it rates severity | How we gate it | What happens on the seeded vulns |
|-------|-----------------------|----------------|----------------------------------|
| **Gitleaks** (secrets) | A secret is a secret | `gitleaks detect` over full history, `--exit-code 1` | **Fails**: seeded AWS key found in history |
| **Trivy** (SCA + image) | Native LOW/MED/HIGH/CRIT | `--severity HIGH,CRITICAL --exit-code 1`, plus a separate `MEDIUM --exit-code 0` pass that only warns; the image scan adds `--ignore-unfixed` | **Fails**: `urllib3` has 6 HIGH CVEs |
| **Checkov** (IaC) | No CVSS, just pass/fail per policy | `--soft-fail` (warn on everything) plus `--hard-fail-on CKV_AWS_53,54,55,56` to gate the serious ones | **Fails**: the public-access checks; the 6 best-practice gaps stay warnings |
| **CodeQL** (SAST) | Alerts in the Security tab | Doesn't fail the workflow step; enforced through **branch protection** (a required "Code scanning" check), see below | Reports `py/sql-injection` (High) as an alert |
| **ZAP** (DAST) | Risk High/Med/Low/Info | Report-only. The app's findings are Low/Med (headers), so per "warn on medium" it doesn't block | Warns about missing security headers |

The interesting case is the pass/fail tool (Checkov): with no CVSS score, **you decide
what counts as serious by choosing which checks gate** (`--hard-fail-on`). "Warn on
medium" becomes "warn on the checks we didn't hard-fail."

The `--ignore-unfixed` on the Trivy image scan is deliberate. The base image carries a
lot of CVEs that have no fix yet, and gating on those would break the build permanently
for something nobody can act on. So only *fixable* HIGH/CRITICAL vulnerabilities gate.

## A verified enforcement run

The commit that enforced the gate policy (and later ones, see the commit history)
produced **4 green, 3 red**. The red checks are the gates correctly blocking the seeded
high/critical vulnerabilities:
https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672

<img width="645" height="358" alt="image" src="https://github.com/user-attachments/assets/4c38f2d2-4d66-4deb-bc0a-fc0e4ff7467e" />

- ❌ Secret Scan (Gitleaks): `leaks found: 1` - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347524
- ❌ SCA & Image Scan (Trivy): `urllib3` HIGH: 6 - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347606
- ❌ IaC Scan (Checkov): `CKV_AWS_53/54/55/56` failed (hard-fail) - https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29792930672/job/88518347555
- ✅ SAST (CodeQL), DAST (ZAP), Lint & Test, Validate (Terraform)

A red build here is a **good** sign: the pipeline spotted the planted vulnerabilities
and blocked them. Fixing a vulnerability turns its stage green again. That's exactly
what the `remediated` branch shows: with all of them fixed, the whole pipeline passes.

## Making the gates hard to bypass (branch protection)

Failing checks only *stop a merge* if the branch is **protected**. Without protection a
red pipeline is just advisory, and someone could still push straight to `main`. The
recommended setup for `main` (GitHub, Settings, Branches, branch protection rule or a
Ruleset):

- **Require a pull request before merging**, so there are no direct pushes to `main`.
- **Require status checks to pass**, with "require branches to be up to date," and mark
  these gating jobs as **required**:
  - `Lint & Test (Python)`
  - `Validate (Terraform)`
  - `Secret Scan (Gitleaks)`
  - `SCA & Image Scan (Trivy)`
  - `IaC Scan (Checkov)`
- **Require the CodeQL code-scanning check** (and/or "no new high-severity alerts").
  This is how CodeQL enforces: it doesn't fail the workflow step, so branch protection
  blocks the merge based on its code-scanning results instead.
- **Don't allow bypassing** the above, including for administrators.

With these rules plus the security-gated `publish` job, insecure code can neither
**merge** (branch protection) nor **deploy** (gated publish).

> **Note for this demo repo:** `main` keeps the seeded vulnerabilities on purpose, so
> its checks are red. Turning on "require status checks" would correctly block every
> merge, which is the whole point but would also halt work on this teaching repo. So
> the setup is **documented here rather than switched on**. In a real project you'd
> enable it, fix the vulns on a branch, and merge only once it's green.
>
> CodeQL and ZAP are **report-only** (they publish to the Security tab but don't fail
> the workflow), so they aren't listed as required *build* checks. CodeQL is enforced
> through the code-scanning branch-protection check above instead.
