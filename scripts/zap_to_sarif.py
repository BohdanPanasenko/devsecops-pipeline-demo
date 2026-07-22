#!/usr/bin/env python3
"""Convert an OWASP ZAP baseline JSON report into SARIF 2.1.0.

ZAP's baseline scan has no native SARIF output, and GitHub code scanning
expects SARIF. DAST findings are URL-based (not source file/line), so we map
each ZAP alert instance to a SARIF result whose "location" is the affected URL
path. Severity is derived from ZAP's riskcode.

Usage: python zap_to_sarif.py <zap.json> <out.sarif>
If the input is missing or empty, an empty (valid) SARIF file is written so the
pipeline can still upload it.
"""

import json
import sys
from urllib.parse import urlparse

RISK = {
    "3": ("error", "8.0"),    
    "2": ("warning", "5.0"),  
    "1": ("note", "3.0"),     
    "0": ("note", "1.0"),    
}


def build_sarif(data):
    rules = {}
    results = []

    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            rule_id = str(
                alert.get("pluginid") or alert.get("alertRef") or alert.get("name", "zap")
            )
            level, severity = RISK.get(str(alert.get("riskcode", "0")), ("note", "1.0"))

            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": alert.get("name", "ZAP Alert"),
                    "shortDescription": {"text": alert.get("name", "ZAP Alert")},
                    "helpUri": "https://www.zaproxy.org/docs/alerts/",
                    "properties": {"security-severity": severity},
                }

            for instance in alert.get("instances") or [{}]:
                full_url = instance.get("uri") or site.get("@name", "")
                path = (urlparse(full_url).path or "/").lstrip("/") or "index"
                results.append({
                    "ruleId": rule_id,
                    "level": level,
                    "message": {"text": f'{alert.get("name", "ZAP Alert")} — {full_url}'},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": path},
                            "region": {"startLine": 1},
                        }
                    }],
                })

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "OWASP ZAP",
                "informationUri": "https://www.zaproxy.org/",
                "rules": list(rules.values()),
            }},
            "results": results,
        }],
    }


def main():
    in_path, out_path = sys.argv[1], sys.argv[2]
    try:
        with open(in_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    sarif = build_sarif(data)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sarif, f, indent=2)

    print(f"Wrote {len(sarif['runs'][0]['results'])} result(s) to {out_path}")


if __name__ == "__main__":
    main()
