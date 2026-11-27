#!/usr/bin/env python3
"""Liveness audit for the mirrored Surge module index.

Collects every external resource URL the modules actually load:
  (a) script-path= URLs in [Script] sections (active lines only)
  (b) RULE-SET URLs in [Rule] sections (active lines only)
  (c) repositoryUrl values from data-source/modules.json
Checks each unique URL once (HEAD first, GET+Range fallback), classifies:
  alive   = final 2xx/3xx
  dead    = 404/410/DNS failure/connection failure/timeout/5xx
  unknown = 403/429/401 (NOT dead — e.g. kelee.one 403s from this VM due to
            Cloudflare bot-blocking; never exclude on unknown alone)
Writes data-source/url_audit.json and data-source/module_url_map.json
(slug -> {resource_urls, repository_url}).
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "data-source", "modules.json")
MDIR = os.path.join(BASE, "site", "m")
AUDIT_OUT = os.path.join(BASE, "data-source", "url_audit.json")
MAP_OUT = os.path.join(BASE, "data-source", "module_url_map.json")

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36",
      "Accept": "*/*"}

SCRIPT_PATH_RE = re.compile(r"script-path\s*=\s*([\"']?)(https?://[^\s,\"']+)\1", re.I)
RULESET_RE = re.compile(r"RULE-SET\s*,\s*(https?://[^,\s\)\"']+)", re.I)
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def clean_url(u: str) -> str:
    return u.strip().strip("\"'").rstrip(".,")


def extract_module_urls(path: str):
    """Return (resource_urls, non_http_notes). Active lines only."""
    urls = set()
    notes = []
    section = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = SECTION_RE.match(line)
            if m:
                section = m.group(1).strip().lower()
                continue
            if line.startswith("#") or line.startswith(";"):
                continue  # commented-out entries are not loaded by Surge
            if section == "script":
                for mm in SCRIPT_PATH_RE.finditer(line):
                    urls.add(clean_url(mm.group(2)))
                # note non-http script-path values (cannot be checked)
                for mm in re.finditer(r"script-path\s*=\s*([^\s,]+)", line, re.I):
                    v = mm.group(1).strip("\"'")
                    if not v.lower().startswith(("http://", "https://")):
                        notes.append(f"non-http script-path: {v[:120]}")
            elif section == "rule":
                for mm in RULESET_RE.finditer(line):
                    urls.add(clean_url(mm.group(1)))
    return urls, notes


def check_url(url: str, timeout: int = 10):
    """Return (status, code, final_url, reason). status in alive/dead/unknown."""
    def classify(code):
        if 200 <= code < 400:
            return "alive"
        if code in (401, 403, 429):
            return "unknown"
        return "dead"  # 404/410/5xx/other 4xx

    def do_request(method, range_header=False):
        headers = dict(UA)
        if range_header:
            headers["Range"] = "bytes=0-1023"
        # Percent-encode non-ASCII path chars (e.g. Chinese filenames);
        # urllib raises UnicodeEncodeError on them otherwise.
        parts = urllib.parse.urlsplit(url)
        safe = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc,
             urllib.parse.quote(parts.path, safe="/"),
             parts.query, parts.fragment))
        req = urllib.request.Request(safe, headers=headers, method=method)
        # opener without proxy env interference, redirects followed by default
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl()

    last_code = None
    last_err = ""
    last_final = url
    for attempt in range(2):
        try:
            code, final = do_request("HEAD")
            last_code, last_final = code, final
            if code in (405, 501, 400, 403):
                # HEAD rejected — try a ranged GET once
                try:
                    code2, final2 = do_request("GET", range_header=True)
                    return classify(code2), code2, final2, f"GET after HEAD {code}"
                except urllib.error.HTTPError as e:
                    return classify(e.code), e.code, url, f"GET after HEAD {code}: HTTP {e.code}"
                except Exception as e:  # noqa: BLE001
                    return "dead", None, url, f"GET after HEAD {code}: {type(e).__name__}: {e}"
            if code == 429:
                return "unknown", code, final, "rate limited (429)"
            return classify(code), code, final, f"HEAD {code}"
        except urllib.error.HTTPError as e:
            code = e.code
            last_code = code
            if code == 429:
                return "unknown", code, url, "rate limited (429)"
            if code in (405, 501, 400, 403):
                try:
                    code2, final2 = do_request("GET", range_header=True)
                    return classify(code2), code2, final2, f"GET after HEAD {code}"
                except urllib.error.HTTPError as e2:
                    return classify(e2.code), e2.code, url, f"GET after HEAD {code}: HTTP {e2.code}"
                except Exception as e2:  # noqa: BLE001
                    return "dead", None, url, f"GET after HEAD {code}: {type(e2).__name__}: {e2}"
            if code >= 500 and attempt == 0:
                time.sleep(1)
                continue  # retry once on 5xx
            return classify(code), code, url, f"HEAD HTTP {code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", e)
            last_err = f"{type(e).__name__}: {reason}"
            if attempt == 0:
                time.sleep(1)
                continue
            return "dead", None, url, last_err
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            if attempt == 0:
                time.sleep(1)
                continue
            return "dead", None, url, last_err
    return "dead", last_code, last_final, last_err or "failed after retries"


def main():
    with open(SRC, encoding="utf-8") as f:
        entries = json.load(f)
    by_slug = {e["slug"]: e for e in entries}

    module_map = {}
    all_urls = set()
    non_http = []
    for slug in sorted(by_slug):
        path = os.path.join(MDIR, f"{slug}.sgmodule")
        if not os.path.exists(path):
            module_map[slug] = {"resource_urls": [], "repository_url": by_slug[slug].get("repositoryUrl") or "",
                                "missing_file": True}
            continue
        urls, notes = extract_module_urls(path)
        repo = by_slug[slug].get("repositoryUrl") or ""
        module_map[slug] = {"resource_urls": sorted(urls), "repository_url": repo}
        all_urls |= urls
        if repo:
            all_urls.add(repo)
        non_http.extend((slug, n) for n in notes)

    print(f"modules: {len(by_slug)}")
    print(f"unique URLs to check: {len(all_urls)} "
          f"(resource {len(all_urls - {e.get('repositoryUrl') for e in entries if e.get('repositoryUrl')})})")
    print(f"non-http script-path notes: {len(non_http)}")

    results = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check_url, u): u for u in sorted(all_urls)}
        done = 0
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                status, code, final, reason = fut.result()
            except Exception as e:  # noqa: BLE001
                status, code, final, reason = "dead", None, u, f"checker error: {e}"
            results[u] = {"url": u, "status": status, "code": code,
                          "final_url": final, "reason": reason,
                          "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            done += 1
            if done % 200 == 0:
                print(f"  checked {done}/{len(all_urls)} ({time.time()-t0:.0f}s)")

    counts = {"alive": 0, "dead": 0, "unknown": 0}
    for r in results.values():
        counts[r["status"]] += 1
    print(f"done in {time.time()-t0:.0f}s: {counts}")

    # per-host breakdown for unknown (spot bot-blocking hosts)
    from urllib.parse import urlparse
    host_unknown = {}
    host_dead = {}
    for r in results.values():
        host = urlparse(r["url"]).netloc
        if r["status"] == "unknown":
            host_unknown[host] = host_unknown.get(host, 0) + 1
        elif r["status"] == "dead":
            host_dead[host] = host_dead.get(host, 0) + 1
    print("top unknown hosts:", sorted(host_unknown.items(), key=lambda kv: -kv[1])[:10])
    print("top dead hosts:", sorted(host_dead.items(), key=lambda kv: -kv[1])[:10])

    with open(AUDIT_OUT, "w", encoding="utf-8") as f:
        json.dump([results[u] for u in sorted(results)], f, ensure_ascii=False, indent=1)
    with open(MAP_OUT, "w", encoding="utf-8") as f:
        json.dump(module_map, f, ensure_ascii=False, indent=1)
    print(f"wrote {AUDIT_OUT} and {MAP_OUT}")
    if non_http:
        print("non-http script-path notes (first 10):")
        for slug, n in non_http[:10]:
            print(f"  {slug}: {n}")


if __name__ == "__main__":
    main()
