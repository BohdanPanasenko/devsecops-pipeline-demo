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
