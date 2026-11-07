"""Grant Use on every asset the game references to Dev's alt (User 347852675) and the tulevo
universe (with dependencies, so meshes/images inside models load in Studio).

  python3 tools/grant_all.py            # grant
  python3 tools/grant_all.py --list     # only print how many ids it found

Ids come from src/shared/*Ids.luau, art/*.lock.json and src/workspace/City.model.json
(LiveSyncAsset + LiveSyncTextures). Needs ROBLOXAPIKEY (asset-permissions:write). Safe to run again.
"""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from upload_anims import request  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUBJECTS = [("User", "347852675", False), ("Universe", "10774732930", True)]


def collect():
    ids = set()
    for p in glob.glob(os.path.join(ROOT, "src", "shared", "*Ids.luau")):
        for m in re.finditer(r"=\s*(?:\"rbxassetid://)?(\d{8,})", open(p, encoding="utf-8").read()):
            ids.add(int(m.group(1)))

    def walk(v):
        if isinstance(v, dict):
            if isinstance(v.get("id"), (int, str)) and str(v["id"]).isdigit():
                ids.add(int(v["id"]))
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for p in glob.glob(os.path.join(ROOT, "art", "*.lock.json")):
        walk(json.load(open(p, encoding="utf-8")))
    city = open(os.path.join(ROOT, "src", "workspace", "City.model.json"), encoding="utf-8").read()
    for m in re.finditer(r'"LiveSyncAsset": (\d+)', city):
        ids.add(int(m.group(1)))
    for m in re.finditer(r'"LiveSyncTextures": "([^"]*)"', city):
        for n in re.findall(r"\d{8,}", m.group(1)):
            ids.add(int(n))
    return sorted(i for i in ids if i > 10_000_000)


def grant(ids):
    report = {}
    for subject, sid, deps in SUBJECTS:
        pending, bad = list(ids), {}
        for attempt in range(5):
            retry = []
            for i in range(0, len(pending), 25):
                chunk = pending[i:i + 25]
                body = {"subjectType": subject, "subjectId": sid, "action": "Use",
                        "requests": [{"assetId": a, "grantToDependencies": deps} for a in chunk]}
                code, r = request("PATCH", "https://apis.roblox.com/asset-permissions-api/v1/assets/permissions",
                                  json.dumps(body).encode(), {"Content-Type": "application/json-patch+json"})
                if code >= 300:
                    print(f"  {subject} {sid}: HTTP {code} {str(r)[:200]}", flush=True)
                    retry += chunk
                    continue
                for e in (r.get("errors") if isinstance(r, dict) else None) or []:
                    a = int(e.get("assetId", 0) or 0)
                    if e.get("code") == "CannotManageAsset" and attempt < 4:
                        retry.append(a)
                    else:
                        bad[a] = e.get("code")
            if not retry:
                break
            pending = retry
            time.sleep(10)
        else:
            for a in pending:
                bad.setdefault(a, "still failing")
        report[f"{subject} {sid}"] = bad
        print(f"{subject} {sid}: {len(ids) - len(bad)}/{len(ids)} granted", flush=True)
    return report


if __name__ == "__main__":
    ids = collect()
    print(f"{len(ids)} asset ids", flush=True)
    if "--list" not in sys.argv:
        rep = grant(ids)
        for who, bad in rep.items():
            codes = {}
            for a, c in bad.items():
                codes.setdefault(c, []).append(a)
            for c, lst in codes.items():
                print(f"  {who}: {len(lst)} x {c} e.g. {lst[:5]}")
