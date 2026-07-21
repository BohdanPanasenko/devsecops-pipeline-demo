# Seeded Vulnerabilities

This app is **deliberately insecure**. The vulnerabilities below were planted on
purpose to demonstrate that each stage of the CI/CD security pipeline detects the
class of problem it is responsible for. Each entry lists what the flaw is, which
scanner is expected to catch it, and the expected severity.

---

## #1 — SQL Injection

- **Where:** [`app.py`](app.py) — the `login()` route.
- **What it is:** User-supplied `username` and `password` are concatenated
  directly into the SQL query string (via `%` formatting) instead of being passed
  as bound parameters. An attacker can inject SQL through the login form.
- **Example exploit:** logging in with username `' OR '1'='1' --` and any
  password makes the query always evaluate true, bypassing authentication.
- **Safe version (before):** the query used parameter binding
  (`execute("... WHERE username = ? AND password = ?", (username, password))`),
  which the driver escapes safely.
- **Scanner expected to catch it:** **CodeQL (SAST)** — query `py/sql-injection`
  (CWE-89). It traces tainted input from the Flask request to the SQL sink.
- **Expected severity:** High / Critical.
- **Where to see the finding:** GitHub repo → **Security → Code scanning**.
- **Status:** ✅ Confirmed — CodeQL reported `py/sql-injection` (High) on
  `app.py` in the Security → Code scanning tab.
  
  <img width="1920" height="968" alt="security2" src="https://github.com/user-attachments/assets/ee1d7115-65ee-4135-846b-4aad053d58aa" />
  
---

## #2 — Hardcoded Secret (fake AWS credential)

- **Where:** [`app.py`](app.py) — module-level constant `AWS_ACCESS_KEY_ID`.
- **What it is:** A credential hardcoded directly in source instead of being read
  from an environment variable or a secrets manager. Anyone with repo access
  (it's a public repo) can read it. The value is **fake**, planted only for the demo.
- **Why the "obvious" dummy didn't work:** a low-entropy string like
  `dummy-not-real-12345` matches no known credential pattern, and AWS's documented
  example key (`AKIAIOSFODNN7EXAMPLE`) is explicitly allowlisted by scanners. A
  detectable secret must have a real credential's *shape* and a *non-allowlisted* value.
- **Scanner expected to catch it:** **Gitleaks** — rule `aws-access-token`
  (matches `AKIA` + 16 chars).
- **Expected severity:** High (secret exposure).
- **Behavior note:** unlike the report-only scanners, the Gitleaks CI job **fails
  the build** on any leak — so this stage turns red, which is the intended gate for secrets.
- **Status:** ✅ Confirmed — Gitleaks failed the CI **Secret Scan** job with
  rule `aws-access-token` on `app.py`, blocking the build (as intended for secrets).

  <img width="1275" height="761" alt="security4" src="https://github.com/user-attachments/assets/61ccdfb0-89d1-4ab7-9f48-79d673dce4f9" />

---

## #3 — Outdated Dependency with Known CVEs

- **Where:** [`requirements.txt`](requirements.txt) — `urllib3==1.24.1` (pinned to a
  years-old release). Declared only for the demo; the app does not import it.
- **What it is:** Depending on a package version with publicly known
  vulnerabilities (CVEs). The risk isn't in code you wrote — it's in third-party
  code you pulled in and shipped.
- **Why this specific version:** `urllib3==1.24.1` is pure-Python (installs from a
  wheel with no compiler), so it doesn't break the build, yet it carries several
  HIGH CVEs (e.g. `CVE-2019-11324`, `CVE-2023-43804`). A tempting CRITICAL pick,
  PyYAML 5.3.1, was rejected because it needs a C compiler unavailable in
  `python:3.12-slim` — a reminder that old dependencies sometimes won't even build.
- **Scanner expected to catch it:** **Trivy** — caught **twice**: the dependency
  (SCA) scan reads `requirements.txt`, and the container image scan finds it
  installed in the built image.
- **Expected severity:** High (6 HIGH findings, 0 CRITICAL at time of writing).
- **Where to see the finding:** the **SCA & Image Scan (Trivy)** job log.
- **Status:** ✅ Confirmed locally (`trivy fs` reported 6 HIGH CVEs for
  `urllib3` 1.24.1); to be re-confirmed by the CI run.

