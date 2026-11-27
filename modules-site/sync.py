#!/usr/bin/env python3
"""Sync the module index from upstream (son.zhiaon.top) — no Muse needed.

- Fetches https://son.zhiaon.top/data/modules.json
- Compares with data-source/modules.json by (slug, version, updatedAt)
- Downloads new/changed .sgmodule files into site/m/
- Deletes files for removed slugs
- Regenerates data-source/SUMMARY.md and re-runs build.py
- Prints a short change summary; no-op (exit 0) when nothing changed.

Usage:
    python3 sync.py [--force]     # --force re-downloads every module file
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

SRC = os.path.join(BASE, "data-source", "modules.json")
SUMMARY = os.path.join(BASE, "data-source", "SUMMARY.md")
EXCLUDED = os.path.join(BASE, "data-source", "excluded.json")
OUTDIR = os.path.join(BASE, "site", "m")
UPSTREAM_URL = "https://son.zhiaon.top/data/modules.json"


def load_excluded():
    """Slugs excluded by the link-liveness audit (data-source/excluded.json).

    Removing a slug from excluded.json re-admits it on the next sync.
    """
    if not os.path.exists(EXCLUDED):
        return []
    with open(EXCLUDED, encoding="utf-8") as f:
        return json.load(f)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"}

try:
    from download_modules import fetch as dl_fetch
    from download_modules import looks_like_module
except ImportError:  # standalone fallback (file copied without download_modules.py)
    def looks_like_module(data: bytes) -> bool:
        if not data:
            return False
        if data[:4096].lstrip().startswith(b"#!"):
            return True
        return any(m in data for m in
                   (b"#!name=", b"[Rule]", b"[Script]", b"[MITM]",
                    b"[URL Rewrite]", b"[Map Local]", b"[General]"))

    def dl_fetch(url: str, timeout: int = 30) -> bytes:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise IOError(f"HTTP {resp.status}")
            return resp.read()


def fetch_upstream(retries: int = 3) -> list:
    last_err = None
    for attempt in range(retries):
        try:
            return json.loads(dl_fetch(UPSTREAM_URL).decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"拉取上游失败: {last_err}")


def download_one(entry, retries: int = 3) -> str:
    """Return '' on success, else an error string."""
    dest = os.path.join(OUTDIR, f"{entry['slug']}.sgmodule")
    last_err = ""
    for attempt in range(retries):
        try:
            data = dl_fetch(entry["rawUrl"])
            if not looks_like_module(data):
                raise IOError("not a module (no header/section marker)")
            with open(dest, "wb") as f:
                f.write(data)
            return ""
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1 + attempt)
    return last_err


def write_summary(entries: list) -> None:
    cats = collections.Counter()
    authors = collections.Counter()
    tags = collections.Counter()
    health = collections.Counter()
    panels = 0
    max_upd = ""
    for e in entries:
        c = (e.get("category") or {}).get("name")
        if c:
            cats[c] += 1
        if e.get("author"):
            authors[e["author"]] += 1
        for t in e.get("tags") or []:
            tags[t] += 1
        health[e.get("health")] += 1
        if e.get("hasPanel"):
            panels += 1
        if (e.get("updatedAt") or "") > max_upd:
            max_upd = e.get("updatedAt") or ""
    with open(SUMMARY, "w", encoding="utf-8") as f:
        f.write("# 上游数据摘要 (son.zhiaon.top/data/modules.json)\n\n")
        f.write(f"- 模块总数：{len(entries)}\n"
                f"- 数据最新更新时间（max updatedAt）：{max_upd}\n"
                f"- 去重作者数：{len(authors)}\n- 带面板模块：{panels}\n"
                f"- 健康状态：{dict(health)}\n")
        excluded = load_excluded()
        if excluded:
            f.write(f"\n## 失效模块排除（{len(excluded)} 个，不发布）\n\n")
            f.write("判定方式：链接存活检测（见 data-source/url_audit.json），而非更新时间——"
                    "上游全部 1511 条的 updatedAt 都在 2026-11，时间上看不出新旧，"
                    "所以失效与否以模块实际加载的外部资源是否还活着为准。\n"
                    "排除规则：全部外部资源 URL 均已失效，或仓库地址 404；"
                    "仅含规则、无外部资源的模块保留；403/429/401 判为未知（例如 kelee.one"
                    " 在本机被 Cloudflare 屏蔽），不作失效处理。\n")
            f.write(f"- 上游总数 {len(entries)} 个，发布 {len(entries) - len(excluded)} 个。\n\n")
            for e in excluded:
                f.write(f"- {e['slug']}（{e.get('name', '')}）：{e.get('reason', '')}\n")
        f.write("\n## 分类统计\n\n")
        for k, v in cats.most_common():
            f.write(f"- {k}：{v}\n")
        f.write("\n## Top 作者\n\n")
        for k, v in authors.most_common(15):
            f.write(f"- {k}：{v}\n")
        f.write("\n## Top 标签\n\n")
        for k, v in tags.most_common(20):
            f.write(f"- {k}：{v}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="re-download every module file")
    args = ap.parse_args()

    try:
        upstream = fetch_upstream()
    except RuntimeError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    if not isinstance(upstream, list) or not upstream:
        print("错误：上游数据为空或格式不对", file=sys.stderr)
        return 1

    old = []
    if os.path.exists(SRC):
        with open(SRC, encoding="utf-8") as f:
            old = json.load(f)
    old_by_slug = {e["slug"]: e for e in old}
    new_by_slug = {e["slug"]: e for e in upstream}

    added = [e for s, e in new_by_slug.items() if s not in old_by_slug]
    removed = [e for s, e in old_by_slug.items() if s not in new_by_slug]
    updated = [e for s, e in new_by_slug.items()
               if s in old_by_slug and (
                   e.get("version") != old_by_slug[s].get("version") or
                   e.get("updatedAt") != old_by_slug[s].get("updatedAt"))]

    if not added and not removed and not updated and not args.force:
        print(f"无变化：上游与本地一致（{len(upstream)} 个模块）")
        return 0

    os.makedirs(OUTDIR, exist_ok=True)
    failures = []
    excluded_slugs = {e["slug"] for e in load_excluded()}
    to_fetch = [e for e in added + updated if e["slug"] not in excluded_slugs]
    if args.force:
        to_fetch = [e for e in upstream if e["slug"] not in excluded_slugs]
    for e in to_fetch:
        err = download_one(e)
        if err:
            failures.append((e["slug"], err))

    for e in removed:
        path = os.path.join(OUTDIR, f"{e['slug']}.sgmodule")
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    # Excluded modules must not linger as files (they would be staged and
    # uploaded to the repo). Removing a slug from excluded.json re-admits it
    # on the next sync (it is re-downloaded then, if still upstream).
    for slug in excluded_slugs:
        path = os.path.join(OUTDIR, f"{slug}.sgmodule")
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(upstream, f, ensure_ascii=False)
    write_summary(upstream)

    r = subprocess.run([sys.executable, os.path.join(BASE, "build.py")],
                       capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        print("错误：build.py 失败，站点未更新", file=sys.stderr)
        return 1

    print(f"同步完成：新增 {len(added)} · 更新 {len(updated)} · 删除 {len(removed)}"
          + (f" · 强制重下 {len(to_fetch)}" if args.force else ""))
    for e in sorted(added, key=lambda x: x["slug"]):
        print(f"  + {e['slug']} v{e.get('version')}")
    for e in sorted(updated, key=lambda x: x["slug"]):
        o = old_by_slug[e["slug"]]
        print(f"  ~ {e['slug']} v{o.get('version')} -> v{e.get('version')}")
    for e in sorted(removed, key=lambda x: x["slug"]):
        print(f"  - {e['slug']} v{e.get('version')}")
    if failures:
        print(f"下载失败 {len(failures)} 个（已保留旧文件）：")
        for slug, err in failures:
            print(f"  ! {slug}: {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
