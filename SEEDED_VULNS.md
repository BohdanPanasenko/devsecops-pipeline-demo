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

