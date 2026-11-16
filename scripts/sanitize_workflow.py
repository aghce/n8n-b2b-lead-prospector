#!/usr/bin/env python3
"""Make an exported n8n workflow safe to publish.

Usage:
    python scripts/sanitize_workflow.py my-export.json workflow/lead-prospector.workflow.json \
        [--company "Example GmbH"] [--replace "Old Name=New Name" ...]

What it does:
  * replaces every credential id/name with a placeholder (you re-select credentials after import)
  * replaces all e-mail addresses with test@example.com (sender: sender@example.com)
  * replaces your company name (default "Grundwerk Digital") with --company
  * clears Telegram chat ids, webhook ids, workflow id, version ids, instance id,
    pinned data and static data, and sets active=false
  * prints every change class so you can review the result before committing

It does NOT remove business logic. Always read the output file once before pushing it.
"""
import argparse
import json
import re
import sys

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")


def sanitize_string(s, replacements, stats):
    def mail(m):
        stats["emails"] += 1
        return "test@example.com"

    out = EMAIL_RE.sub(mail, s)
    for old, new in replacements:
        if old in out:
            stats["names"] += out.count(old)
            out = out.replace(old, new)
    return out


def walk(obj, replacements, stats):
    if isinstance(obj, dict):
        return {k: walk(v, replacements, stats) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(v, replacements, stats) for v in obj]
    if isinstance(obj, str):
        return sanitize_string(obj, replacements, stats)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--company", default="Example GmbH", help="replacement for 'Grundwerk Digital'")
    ap.add_argument("--replace", action="append", default=[], help="OLD=NEW, can be repeated")
    args = ap.parse_args()

    with open(args.src, encoding="utf-8") as f:
        wf = json.load(f)

    replacements = [("Grundwerk Digital", args.company), ("Grundwerk", args.company.split()[0])]
    for pair in args.replace:
        if "=" not in pair:
            sys.exit("--replace needs OLD=NEW")
        old, new = pair.split("=", 1)
        replacements.insert(0, (old, new))

    stats = {"emails": 0, "names": 0, "credentials": 0, "ids": 0}

    for node in wf.get("nodes", []):
        creds = node.get("credentials")
        if creds:
            for ctype in list(creds):
                creds[ctype] = {"id": "REPLACE_ME", "name": f"{ctype} (select your own)"}
                stats["credentials"] += 1
        if "webhookId" in node:
            del node["webhookId"]
            stats["ids"] += 1

    wf = walk(wf, replacements, stats)

    # sender address of the SMTP node should look like a sender, not like the test recipient
    for node in wf.get("nodes", []):
        p = node.get("parameters", {})
        if node.get("type", "").endswith("emailSend") and "fromEmail" in p:
            p["fromEmail"] = "sender@example.com"
        # telegram chat id lives in Workflow Config as an assignment
        for a in p.get("assignments", {}).get("assignments", []):
            if a.get("name") == "telegram_chat_id":
                a["value"] = ""
            if a.get("name") == "test_recipient":
                a["value"] = "test@example.com"

    for key in ("id", "versionId", "activeVersionId", "pinData", "staticData", "shared", "tags", "triggerCount"):
        if key in wf:
            wf.pop(key)
            stats["ids"] += 1
    wf["active"] = False
    if isinstance(wf.get("meta"), dict):
        wf["meta"].pop("instanceId", None)

    with open(args.dst, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)

    print("sanitized ->", args.dst)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    left = EMAIL_RE.findall(json.dumps(wf))
    extra = sorted(set(e for e in left if e not in ("test@example.com", "sender@example.com")))
    if extra:
        print("WARNING: remaining e-mail-like strings:", extra)


if __name__ == "__main__":
    main()
