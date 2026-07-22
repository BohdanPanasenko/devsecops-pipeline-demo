#!/usr/bin/env python3
"""Build one CSV metrics row for a pipeline run: durations + findings-by-severity.

Inputs (JSON already fetched via `gh api`):
  jobs.json    -> GET /repos/{repo}/actions/runs/{id}/jobs
  alerts.json  -> GET /repos/{repo}/code-scanning/alerts?state=open
"""

import datetime
import json
import sys

NAME_TO_KEY = {
    "Lint & Test (Python)": "lint_test",
    "Validate (Terraform)": "terraform",
    "Secret Scan (Gitleaks)": "gitleaks",
    "SAST (CodeQL)": "codeql",
    "SCA & Image Scan (Trivy)": "trivy",
    "IaC Scan (Checkov)": "checkov",
    "DAST (OWASP ZAP)": "zap",
}
STAGE_KEYS = ["lint_test", "terraform", "gitleaks", "codeql", "trivy", "checkov", "zap"]


def parse(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def duration(job):
    s, c = job.get("started_at"), job.get("completed_at")
    if not s or not c:
        return 0
    return int((parse(c) - parse(s)).total_seconds())


def main():
    jobs_path, alerts_path, run_id, sha, ts = sys.argv[1:6]
    jobs = json.load(open(jobs_path, encoding="utf-8")).get("jobs", [])
    alerts = json.load(open(alerts_path, encoding="utf-8"))

    stage = {k: 0 for k in STAGE_KEYS}
    starts, ends = [], []
    for j in jobs:
        key = NAME_TO_KEY.get(j.get("name", ""))
        if key:
            stage[key] = duration(j)
        if j.get("started_at"):
            starts.append(j["started_at"])
        if j.get("completed_at"):
            ends.append(j["completed_at"])
    total = int((parse(max(ends)) - parse(min(starts))).total_seconds()) if starts and ends else 0

    sev = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for a in alerts:
        level = (a.get("rule") or {}).get("security_severity_level")
        sev[level if level in sev else "unknown"] += 1
    total_findings = len(alerts)

    row = [ts, run_id, sha[:7], total] + [stage[k] for k in STAGE_KEYS] + [
        total_findings, sev["critical"], sev["high"], sev["medium"], sev["low"], sev["unknown"],
    ]
    print(",".join(str(x) for x in row))


if __name__ == "__main__":
    main()
