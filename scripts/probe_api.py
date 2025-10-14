#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8000"
SAMPLE_APPID = 10

if len(sys.argv) > 1:
    BASE = sys.argv[1].rstrip('/')
if len(sys.argv) > 2:
    try:
        SAMPLE_APPID = int(sys.argv[2])
    except ValueError:
        pass

endpoints = [
    ("/health", None),
    ("/api/ml/discount-30d/metrics", None),
    ("/api/ml/discount-30d/model-info", None),
    (f"/api/ml/discount-30d?{urlencode({'appid': SAMPLE_APPID})}", None),
]

def fetch(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            print(f"Status: {resp.status}")
            try:
                data = json.loads(body.decode("utf-8"))
                preview = json.dumps(data, ensure_ascii=False)[:500]
            except Exception:
                preview = body[:500]
            print(preview)
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        try:
            body = e.read().decode("utf-8")
            print(body[:500])
        except Exception:
            pass
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

print(f"Probing API base: {BASE}")
for path, _ in endpoints:
    url = f"{BASE}{path}"
    print(f"\nGET {url}")
    fetch(url)
print("\nDone.")
