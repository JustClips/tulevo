"""Grant Use on models (and all their texture Images) to the tulevo universe and Dev's alt.

  python3 tools/grant_universe.py Model [Model ...]

Fresh uploads often answer CannotManageAsset to the first grant; this retries. Without the
universe grant Dev's Studio shows the buildings grey.
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from upload_anims import request  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUBJECTS = [("Universe", "10774732930"), ("User", "347852675")]


def ids_for(models):
    lock = json.load(open(os.path.join(ROOT, "art", "models.lock.json")))
    tlock = json.load(open(os.path.join(ROOT, "art", "textures.lock.json")))
    ids = set()
    for m in models:
        ids.add(int(lock[m]["id"]))
        for rel in json.load(open(os.path.join(ROOT, "art", "models", m, "textures.json"))).values():
            h = hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()
            if h in tlock:
                ids.add(int(tlock[h]["id"]))
    return sorted(ids)


def grant(ids):
    pending = list(ids)
    for attempt in range(8):
        failed = set()
        for subject, sid in SUBJECTS:
            for i in range(0, len(pending), 25):
                chunk = pending[i:i + 25]
                body = {"subjectType": subject, "subjectId": sid, "action": "Use",
                        "requests": [{"assetId": a, "grantToDependencies": subject == "Universe"} for a in chunk]}
                code, r = request("PATCH", "https://apis.roblox.com/asset-permissions-api/v1/assets/permissions",
                                  json.dumps(body).encode(), {"Content-Type": "application/json-patch+json"})
                errs = (r.get("errors") if isinstance(r, dict) else None) or []
                if code >= 300:
                    print(f"  {subject}: {code} {r}")
                    failed.update(chunk)
                for e in errs:
                    failed.add(int(e.get("assetId", 0)))
        failed.discard(0)
        print(f"attempt {attempt + 1}: {len(pending)} assets, {len(failed)} to retry")
        if not failed:
            return True
        pending = sorted(failed)
        time.sleep(15)
    print("still failing:", pending)
    return False


if __name__ == "__main__":
    grant(ids_for(sys.argv[1:]))
