# Seeded Vulnerabilities

This app is insecure on purpose. Each vulnerability below was planted to check that a
stage of the pipeline really catches the kind of problem it's meant to. Every entry
says what the flaw is, which scanner should catch it, and how serious it is.

All of these are fixed on the `remediated` branch, where the pipeline passes every
gate. `main` keeps them on purpose, so the scanners always have something to find.

The two that can be exploited at runtime, the SQL injection (#1) and the reflected
XSS (#6), are what the **ZAP active scan** attacks directly. That scan is the
project's automated penetration testing, and these write-ups are the exploits it
confirms.

---

## #1: SQL Injection

- **Where:** [`app.py`](app.py), the `login()` route.
- **What it is:** the user's `username` and `password` get pasted straight into the SQL
  query string (with `%` formatting) instead of being passed as bound parameters, so an
  attacker can inject SQL through the login form.
- **Example exploit:** logging in with the username `' OR '1'='1' --` and any password
  makes the query always true, which bypasses the login.
- **Safe version (before):** the query used parameter binding
  (`execute("... WHERE username = ? AND password = ?", (username, password))`), which
  the driver escapes safely.
- **Scanner that catches it:** **CodeQL (SAST)**, query `py/sql-injection` (CWE-89). It
  follows untrusted input from the Flask request to the SQL call.
- **Severity:** High / Critical.
- **Where to see it:** the repo's **Security > Code scanning** tab.
- **Status:** ✅ Confirmed. CodeQL reported `py/sql-injection` (High) on `app.py` in the
  Security > Code scanning tab.

  <img width="1920" height="968" alt="security2" src="https://github.com/user-attachments/assets/ee1d7115-65ee-4135-846b-4aad053d58aa" />

---

## #2: Hardcoded Secret (fake AWS credential)

- **Where:** [`app.py`](app.py), the module-level constant `AWS_ACCESS_KEY_ID`.
- **What it is:** a credential written straight into the source instead of coming from
  an environment variable or a secrets manager. Anyone with repo access (it's a public
  repo) can read it. The value is **fake**, planted only for the demo.
- **Why the "obvious" dummy didn't work:** a low-entropy string like
  `dummy-not-real-12345` matches no known credential pattern, and AWS's documented
  example key (`AKIAIOSFODNN7EXAMPLE`) is allowlisted by scanners on purpose. To be
  detected, a secret needs a real credential's *shape* and a value that isn't allowlisted.
- **Scanner that catches it:** **Gitleaks**, rule `aws-access-token` (matches `AKIA`
  plus 16 characters).
- **Severity:** High (secret exposure).
- **Behavior note:** unlike the report-only scanners, the Gitleaks job **fails the
  build** on any leak, so this stage turns red. That's the intended gate for secrets.
- **Status:** ✅ Confirmed. Gitleaks failed the CI **Secret Scan** job with rule
  `aws-access-token` on `app.py`, blocking the build (as intended for secrets). You can
  also see it here: https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29789649954/job/88508446927

  <img width="1275" height="761" alt="security4" src="https://github.com/user-attachments/assets/61ccdfb0-89d1-4ab7-9f48-79d673dce4f9" />

---

## #3: Outdated Dependency with Known CVEs

- **Where:** [`requirements.txt`](requirements.txt), `urllib3==1.24.1` (pinned to a
  years-old release). It's declared only for the demo; the app doesn't import it.
- **What it is:** depending on a package version with publicly known vulnerabilities
  (CVEs). The risk isn't in code you wrote, it's in third-party code you pulled in and
  shipped.
- **Why this specific version:** `urllib3==1.24.1` is pure Python (it installs from a
  wheel, no compiler needed), so it doesn't break the build, but it carries several
  HIGH CVEs (for example `CVE-2019-11324` and `CVE-2023-43804`). A tempting CRITICAL
  pick, PyYAML 5.3.1, was dropped because it needs a C compiler that isn't in
  `python:3.12-slim`, a reminder that old dependencies sometimes won't even build.
- **Scanner that catches it:** **Trivy**, and it catches it **twice**: the dependency
  (SCA) scan reads `requirements.txt`, and the container image scan finds it installed
  in the built image.
- **Severity:** High (6 HIGH findings, 0 CRITICAL at the time of writing).
- **Where to see it:** the **SCA & Image Scan (Trivy)** job log.
- **Status:** ✅ Confirmed. The CI **SCA & Image Scan (Trivy)** job reported 6 HIGH CVEs
  for `urllib3` 1.24.1 in the dependency scan step (the build stayed green, since Trivy
  was report-only at that point). You can also see it here: https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29790414173/job/88510790112

  <img width="1164" height="994" alt="security_trivy" src="https://github.com/user-attachments/assets/cf9d7c8b-f7b0-41c3-b0a3-7113e57546c6" />

---

## #4: Insecure Infrastructure Misconfiguration (public S3 bucket)

- **Where:** [`terraform/main.tf`](terraform/main.tf), the
  `aws_s3_bucket_public_access_block` resource.
- **What it is:** the four public-access guardrails were flipped from `true` to `false`.
  Those settings are what stop an S3 bucket from ever being made public, and turning
  them off lets a public ACL or bucket policy expose the data. It's the classic cause of
  real-world S3 leaks.
- **Safe version (before):** all four set to `true` (the bucket can't be public).
- **Scanner that catches it:** **Checkov**, checks `CKV_AWS_53`, `CKV_AWS_54`,
  `CKV_AWS_55`, `CKV_AWS_56` (and `CKV2_AWS_6`).
- **Severity:** high impact (public data exposure). Checkov OSS reports pass/fail rather
  than a CVSS score, so this is treated as high-impact.
- **Before/after:** Checkov failures went from **5** (baseline best-practice gaps) to
  **10** once the guardrails were disabled.
- **Where to see it:** the **IaC Scan (Checkov)** job log.
- **Status:** ✅ Confirmed. The CI **IaC Scan (Checkov)** job reported
  `Passed: 6, Failed: 10`, with `CKV_AWS_53/54/55/56` failing (the build stayed green,
  since Checkov runs with `--soft-fail` until the gate). You can also see it here: https://github.com/BohdanPanasenko/devsecops-pipeline-demo/actions/runs/29791109667/job/88512903816

  <img width="1299" height="974" alt="security_vuln4" src="https://github.com/user-attachments/assets/5d94ed95-bae9-4fea-a89d-060853c71c53" />

---

## #5: Broken Access Control (the scanner blind spot)

- **Where:** [`app.py`](app.py), the `/items` route.
- **What it is:** any logged-in user sees **all** items, no matter the `owner` column.
  There's no check tying items to the current user, so `alice` can see `bob`'s items.
  It's a business-logic / authorization flaw (OWASP A01: Broken Access Control).
- **Why it's the important case:** **no scanner in the pipeline catches it.**
  - **CodeQL (SAST)** sees valid code with no dangerous sink, so there's nothing to flag.
  - **Trivy (SCA/image)** finds no vulnerable dependency.
  - **Checkov (IaC)** sees no infrastructure problem.
  - **ZAP (DAST)** has no way to know the *intended* rules, so it can't tell that
    showing all items is wrong.
- **Scanner that catches it:** **None.** This is the pipeline's blind spot.
- **Severity:** High (unauthorized data access), yet nothing in the tooling flags it.
- **Note:** automated scanning covers whole classes of technical vulnerability cheaply
  and repeatably, but it **adds to, rather than replaces**, human review, threat
  modeling, and manual testing. Business-logic flaws need a person who understands what
  the app is *supposed* to do.
- **Status:** ✅ Verified as a blind spot. It's present in the code and reported by none
  of the five security stages.

  <img width="413" height="365" alt="image" src="https://github.com/user-attachments/assets/89657a86-3f24-49cb-aec6-81bb728dcf1b" />

---

## #6: Reflected XSS (the DAST target)

- **Where:** [`app.py`](app.py), the public `/search` route echoes the `q` query
  parameter straight into the HTML response without escaping.
- **What it is:** reflected Cross-Site Scripting. A request like
  `/search?q=<script>alert(1)</script>` returns that script in the page, so it runs in
  the victim's browser (session theft, defacement, and so on).
- **Why it exists:** to give **DAST a real target**. The ZAP baseline (passive) scan only
  notices missing headers; only an **active** scan fires payloads and finds an injectable
  flaw. So the ZAP stage was switched from `zap-baseline.py` to `zap-full-scan.py`
  (active), and a link to `/search?q=test` was added so ZAP's spider finds the parameter.
- **Scanner that catches it:** **OWASP ZAP (DAST)**, `Cross Site Scripting (Reflected)`
  (High). **CodeQL (SAST)** is expected to flag it too (`py/reflective-xss`).
- **The headline point:** SAST and DAST catch the *same* flaw from opposite ends, one by
  reading the source and the other by attacking the running app. ZAP's active scan also
  re-discovered the **#1 SQL injection** at runtime, which confirms the same overlap.
- **Severity:** High.
- **Where to see it:** **Security > Code scanning** (tool `zap`), and the DAST job log.
- **Status:** ✅ Confirmed in CI. The `OWASP ZAP` tool reports `Cross Site Scripting
  (Reflected)` (rule 40012) and `SQL Injection` (rule 40018) as High in the Security
  tab. The same SQLi and XSS also show up from **CodeQL**, confirming that SAST and DAST
  catch the identical flaws from opposite ends.

  <img width="1910" height="407" alt="image" src="https://github.com/user-attachments/assets/d558f9b5-8b80-48c2-8584-96afd43bb849" />

  <img width="1366" height="812" alt="image" src="https://github.com/user-attachments/assets/3bb35952-6c45-4e63-a34e-ef20609160bd" />
