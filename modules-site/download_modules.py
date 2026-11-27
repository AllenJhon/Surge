#!/usr/bin/env python3
"""Download every .sgmodule file listed in data-source/modules.json.

Usage: python3 download_modules.py [--workers N] [--retries N]
Writes files to site/m/<slug>.sgmodule and failures to
data-source/download_failures.txt (one slug per line: slug, url, reason).
Safe to re-run: skips files that already exist and pass validation.
"""
import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "data-source", "modules.json")
OUTDIR = os.path.join(BASE, "site", "m")
FAILFILE = os.path.join(BASE, "data-source", "download_failures.txt")

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"}

MARKERS = (b"#!name=", b"#!desc=", b"[Rule]", b"[Script]", b"[MITM]",
           b"[URL Rewrite]", b"[Map Local]", b"[General]", b"[Host]",
           b"[Panel]", b"[Header Rewrite]", b"[Body Rewrite]")


def looks_like_module(data: bytes) -> bool:
    if not data:
        return False
    head = data[:4096]
    if head.lstrip().startswith(b"#!"):
        return True
    return any(m in data for m in MARKERS)


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise IOError(f"HTTP {resp.status}")
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0,
                    help="only download the first N entries (debug)")
    args = ap.parse_args()

    entries = json.load(open(SRC, encoding="utf-8"))
    if args.limit:
        entries = entries[: args.limit]
    # Dead modules (link-liveness audit) are not downloaded: removing a slug
    # from data-source/excluded.json re-admits it on the next run.
    excl_path = os.path.join(BASE, "data-source", "excluded.json")
    excluded = set()
    if os.path.exists(excl_path):
        with open(excl_path, encoding="utf-8") as f:
            excluded = {e["slug"] for e in json.load(f)}
    entries = [e for e in entries if e.get("slug") not in excluded]
    for slug in excluded:
        try:
            os.remove(os.path.join(OUTDIR, f"{slug}.sgmodule"))
        except FileNotFoundError:
            pass
    os.makedirs(OUTDIR, exist_ok=True)

    total_bytes = 0
    ok = 0
    failed = []  # (slug, url, reason)
    skipped = 0
    lock = threading.Lock()
    done = 0

    def work(entry):
        nonlocal total_bytes, ok, skipped, done
        slug = entry["slug"]
        url = entry["rawUrl"]
        dest = os.path.join(OUTDIR, f"{slug}.sgmodule")
        if os.path.exists(dest):
            try:
                with open(dest, "rb") as f:
                    if looks_like_module(f.read()):
                        with lock:
                            skipped += 1
                            done += 1
                        return
            except OSError:
                pass
        last_err = ""
        for attempt in range(args.retries + 1):
            try:
                data = fetch(url)
                if not looks_like_module(data):
                    raise IOError("not a module (no header/section marker)")
                with open(dest, "wb") as f:
                    f.write(data)
                with lock:
                    ok += 1
                    total_bytes += len(data)
                    done += 1
                return
            except Exception as e:  # noqa: BLE001 - record and retry
                last_err = f"{type(e).__name__}: {e}"
                if "429" in last_err or "403" in last_err:
                    time.sleep(5)
                elif attempt < args.retries:
                    time.sleep(1 + attempt)
        with lock:
            failed.append((slug, url, last_err))
            done += 1

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers) as pool:
        list(pool.map(work, entries))
    dt = time.time() - t0

    with open(FAILFILE, "w", encoding="utf-8") as f:
        for slug, url, reason in sorted(failed):
            f.write(f"{slug}\t{url}\t{reason}\n")

    print(f"entries: {len(entries)}  downloaded: {ok}  skipped(valid): {skipped}  "
          f"failed: {len(failed)}  bytes: {total_bytes}  elapsed: {dt:.1f}s")
    if failed:
        print("failures (first 20):")
        for slug, url, reason in sorted(failed)[:20]:
            print(f"  {slug}: {reason}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
