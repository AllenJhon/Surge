#!/usr/bin/env python3
"""Build the static Surge module index site.

Reads data-source/modules.json, rewrites each entry's rawUrl to the local
relative path /m/<slug>.sgmodule (original kept as upstreamUrl), writes
site/data/modules.json, and generates site/index.html — one HTML file with
inline CSS + JS and the module data embedded, so it works from any static
host and from file://. The header logo is the Surge app icon, embedded as a
base64 data URI (source: fmz200 icon collection, re-fetchable from
https://raw.githubusercontent.com/fmz200/wool_scripts/main/icons/apps/Surge.png),
so the page stays a single file. Visual language follows son.zhiaon.top
(许舟's Surge Modules index) — indigo accent, hairline borders, Inter type,
numbered section eyebrows, category-first cards, light/dark themes — rebuilt
with our own code and copy; no upstream assets are copied. The homepage
mirrors his current layout: Chinese hero with gradient headline and four
stat cards, 本期推荐 (empty state), 按用途浏览， 最近更新， 全部模块
preview, and the 关于平台 intro block.

Usage: python3 build.py
Safe to re-run; output is fully deterministic — the snapshot stamp comes
from the data's max updatedAt, never wall-clock time, so an unchanged
upstream produces byte-identical output (no empty sync commits).
"""
import json
import os
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "data-source", "modules.json")
OUT_DATA = os.path.join(BASE, "site", "data", "modules.json")
OUT_HTML = os.path.join(BASE, "site", "index.html")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Surge Modules</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@latest/index.css">
<script>try{var __t=localStorage.getItem('surge-index-theme');if(!__t)__t=(window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)?'light':'dark';document.documentElement.setAttribute('data-theme',__t);document.documentElement.style.colorScheme=__t;}catch(__e){}</script>
<link rel="icon" type="image/png" href="data:image/png;base64,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">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{color-scheme:dark}
:root,[data-theme="dark"]{--bg:#0b0d12;--surface:#10141c;--card:#151a23;--hover:#1b2230;--inset:#0d1017;--float:#1b2230;--text:#f1f5f9;--muted:#a1aab8;--faint:#828e9e;--line:rgba(255,255,255,.08);--line-strong:rgba(255,255,255,.16);--accent:#8b9cff;--accent-strong:#6d80f5;--accent-soft:#b8c3ff;--accent-fg:#0b0d12;--accent-tint:rgba(139,156,255,.12);--ok:#35c98a;--ok-bg:rgba(53,201,138,.13);--warn:#e8b65c;--warn-bg:rgba(232,182,92,.13);--danger:#f07178;--scrim:rgba(5,7,11,.66);--star:#f5a623;--shadow-sm:0 1px 2px rgba(0,0,0,.35),0 4px 12px rgba(0,0,0,.28);--shadow-md:0 2px 6px rgba(0,0,0,.4),0 12px 32px rgba(0,0,0,.38);--glass-bg:rgba(21,26,35,.55);--glass-line:rgba(255,255,255,.22);--glass-hi:rgba(255,255,255,.32)}
[data-theme="light"]{color-scheme:light;--bg:#f6f7fa;--surface:#eff1f6;--card:#fff;--hover:#f7f8fc;--inset:#f1f3f8;--float:#fff;--text:#171b25;--muted:#5e6877;--faint:#616b7d;--line:#e8ebf0;--line-strong:#d6dae3;--accent:#6578e8;--accent-strong:#5566d8;--accent-soft:#4553c4;--accent-fg:#fff;--accent-tint:rgba(101,120,232,.12);--ok:#17794f;--ok-bg:rgba(23,121,79,.12);--warn:#8a6412;--warn-bg:rgba(138,100,18,.12);--danger:#b93a43;--scrim:rgba(23,27,37,.34);--star:#d97706;--shadow-sm:0 1px 2px rgba(16,24,40,.07),0 4px 12px rgba(16,24,40,.08);--shadow-md:0 2px 6px rgba(16,24,40,.1),0 12px 32px rgba(16,24,40,.14);--glass-bg:rgba(255,255,255,.55);--glass-line:rgba(255,255,255,.65);--glass-hi:rgba(255,255,255,.7)}
body{font-family:"Inter Variable",Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);font-size:15px;line-height:1.5}
header{position:sticky;top:0;z-index:30;background:var(--bg);background:color-mix(in srgb,var(--bg) 88%,transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.header-in{max-width:1060px;margin:0 auto;padding:0 16px;height:57px;display:flex;align-items:center;gap:12px}
.brand{display:flex;align-items:center;gap:10px;min-width:0}
img.logo{width:32px;height:32px;border-radius:8px;background:#fff;object-fit:cover;flex:0 0 auto}
header h1{font-size:17px;font-weight:650;letter-spacing:-.01em;white-space:nowrap}
.topnav{display:none;gap:2px;margin-left:6px}
@media(min-width:820px){.topnav{display:flex}}
.topnav button{background:none;border:none;color:var(--muted);font-size:14px;font-weight:500;padding:7px 11px;border-radius:8px;cursor:pointer;font-family:inherit}
.topnav button:hover{color:var(--text);background:var(--hover)}
.topnav button.on{color:var(--accent)}
.theme-btn{margin-left:auto;width:36px;height:36px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.theme-btn:hover{color:var(--text);border-color:var(--line-strong)}
.sub-head{padding:28px 4px 4px}
.sub-head h1{font-size:clamp(30px,7vw,38px);font-weight:600;letter-spacing:-.028em;line-height:1.08;margin-top:10px}
.sub-head p{color:var(--muted);font-size:14px;margin-top:12px;line-height:1.7;max-width:560px}
.disc-tools{position:sticky;top:57px;z-index:20;padding:14px 0 12px;background:color-mix(in srgb,var(--bg) 92%,transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px)}
.disc-tools-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
.sortseg{display:flex;gap:2px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:2px;overflow-x:auto;scrollbar-width:none}
.sortseg::-webkit-scrollbar{display:none}
.sortseg button{border:none;background:none;color:var(--faint);font-size:12px;padding:8px 10px;border-radius:8px;cursor:pointer;white-space:nowrap;font-family:inherit}
.sortseg button.on{background:var(--hover);color:var(--text)}
.filter-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-left:4px;vertical-align:2px}
.filter-panel{margin-top:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
@media(min-width:1024px){.filter-panel{padding:20px}}
.fp-head{display:flex;align-items:center;justify-content:space-between}
.fp-head b{font-size:13.5px}
.fp-close{border:none;background:none;color:var(--muted);cursor:pointer;font-size:14px;padding:4px 8px;border-radius:999px;font-family:inherit}
.fp-close:hover{background:var(--hover);color:var(--text)}
.fp-grid{margin-top:10px;display:grid;gap:12px}
@media(min-width:1024px){.fp-grid{grid-template-columns:1fr 1.5fr;gap:16px 24px}}
.fp-label{font-size:11.5px;color:var(--faint);margin-bottom:8px}
.fchips{display:flex;flex-wrap:wrap;gap:4px}
.fchip{display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 8px;border:1px solid var(--line);border-radius:6px;background:var(--inset);color:var(--muted);font-size:10px;cursor:pointer;white-space:nowrap;font-family:inherit}
@media(min-width:1024px){.fchip{height:28px;padding:0 10px;font-size:11.5px}}
.fchip.on{border-color:var(--accent);background:var(--accent-tint);color:var(--accent-soft)}
.fchip img{width:14px;height:14px;border-radius:50%;object-fit:cover}
.fchip small{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9.5px;opacity:.6}
.fp-reset{margin-top:12px;border:none;background:none;color:var(--muted);font-size:11.5px;cursor:pointer;text-decoration:underline;text-underline-offset:4px;font-family:inherit}
.fp-reset:hover{color:var(--text)}
.active-filters{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:16px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.active-filters .af-label{font-size:11.5px;color:var(--faint)}
.af-chip{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--accent);background:var(--accent-tint);color:var(--accent-soft);border-radius:999px;padding:4px 4px 4px 10px;font-size:11.5px}
.af-chip button{border:none;background:none;color:inherit;cursor:pointer;font-size:12px;padding:0 4px;border-radius:50%;font-family:inherit}
.af-clear{margin-left:auto;border:none;background:none;color:var(--muted);font-size:11.5px;cursor:pointer;text-decoration:underline;text-underline-offset:4px;font-family:inherit}
.af-clear:hover{color:var(--text)}
.res-count{margin-top:20px;font-size:11.5px;color:var(--faint)}
.pager{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:24px}
.pager button{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--muted);font-size:18px;cursor:pointer;font-family:inherit}
.pager button:hover:not(:disabled){border-color:var(--line-strong);color:var(--text)}
.pager button:disabled{opacity:.35;cursor:default}
.pager span{min-width:80px;text-align:center;font-size:12px;color:var(--faint);font-variant-numeric:tabular-nums}
.disc-cats{margin-top:64px;border-top:1px solid var(--line);padding-top:48px}
.disc-cats h2{font-size:24px;font-weight:600;letter-spacing:-.02em}
.disc-cats .sec-sub{margin-top:8px}
.fav-count-line{display:flex;align-items:baseline;gap:8px;font-size:12px;color:var(--faint);margin-top:28px}
.fav-count-line .fav-num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;color:var(--text)}
.fav-item{display:flex;flex-direction:column;gap:6px;min-width:0}
.fav-time{padding-left:4px;font-size:10.5px;color:var(--faint)}
.fav-note{margin-top:40px;border-top:1px solid var(--line);padding-top:20px;font-size:11px;line-height:1.7;color:var(--faint)}
.upd-layout{display:grid;grid-template-columns:1fr;gap:32px;margin-top:28px}
@media(min-width:1024px){.upd-layout{grid-template-columns:minmax(0,1fr) 320px;gap:48px}}
.upd-sec-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.upd-sec-head h2{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--faint)}
.upd-sec-head span{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--faint)}
.upd-day{margin-bottom:32px}
.upd-day-head{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.upd-day-head h3{font-size:12px;font-weight:500;color:var(--muted)}
.upd-day-line{flex:1;height:1px;background:var(--line)}
.upd-day-count{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;color:var(--faint)}
.upd-rows{display:flex;flex-direction:column;gap:10px}
.ver-badge{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted);background:var(--inset);border:1px solid var(--line);border-radius:6px;padding:2px 7px}
.latest-badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--ok);background:var(--ok-bg);border-radius:999px;padding:2px 8px}
.latest-dot{width:4px;height:4px;border-radius:50%;background:var(--ok)}
.ann-empty{border:1px dashed var(--line);border-radius:14px;padding:32px 16px;text-align:center;color:var(--faint);font-size:12.5px}
.searchrow{display:flex;gap:8px}
#q{flex:1;padding:11px 12px;font-size:16px;border:1px solid var(--line);border-radius:10px;background:var(--inset);color:var(--text);outline:none}
#q:focus{border-color:var(--accent)}
.btn{padding:0 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);font-size:14px;cursor:pointer;white-space:nowrap;font-family:inherit}
.btn.on{background:var(--accent);border-color:var(--accent);color:var(--accent-fg)}
main{padding:12px;max-width:1060px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
@property --rb-angle{syntax:'<angle>';initial-value:0deg;inherits:false}
@keyframes rb-spin{to{--rb-angle:360deg}}
.card::before,.upd-row::before,.catcard::before,.statcard::before{content:'';position:absolute;inset:0;border-radius:inherit;padding:1.5px;background:conic-gradient(from var(--rb-angle,0deg),#ff2d78,#ff8a00,#ffe600,#2ee66b,#00c2ff,#7a5cff,#ff2d78);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);mask-composite:exclude;animation:none;pointer-events:none}
.card:hover::before,.upd-row:hover::before,.catcard:hover::before,.statcard:hover::before,.card:active::before,.upd-row:active::before,.catcard:active::before,.statcard:active::before,.card.is-new::before{animation:rb-spin 5s linear infinite}
@media (prefers-reduced-motion:reduce){.card::before,.upd-row::before,.catcard::before,.statcard::before,.card:hover::before,.upd-row:hover::before,.catcard:hover::before,.statcard:hover::before,.card:active::before,.upd-row:active::before,.catcard:active::before,.statcard:active::before,.card.is-new::before{animation:none}}
.card{background:var(--glass-bg);-webkit-backdrop-filter:blur(20px) saturate(160%);backdrop-filter:blur(20px) saturate(160%);border:1px solid var(--glass-line);border-radius:18px;padding:16px;cursor:pointer;position:relative;box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-sm);transition:transform .2s,box-shadow .2s,border-color .2s,background .2s}
.card:hover{border-color:var(--glass-hi);background:color-mix(in srgb,var(--glass-bg) 82%,#fff 18%);transform:translateY(-2px);box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-md)}
.card-top{display:flex;align-items:baseline;gap:6px;font-size:12px;color:var(--faint);padding-right:30px}
.card-top .cat{color:var(--muted);font-weight:500}
.card-top .ver{color:var(--faint)}
.card-top .badge{margin-left:auto}
.card h3{font-size:17px;font-weight:600;letter-spacing:-.01em;padding-right:30px;margin-top:5px}
.meta{font-size:12.5px;color:var(--faint);margin-top:5px}
.desc{font-size:14px;color:var(--muted);margin-top:8px;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tags{margin-top:10px;display:flex;flex-wrap:wrap;gap:5px}
.tag{background:var(--inset);border-radius:6px;padding:2px 7px;font-size:12px;color:var(--muted)}
.badge{display:inline-block;border-radius:6px;padding:2px 7px;font-size:11.5px;margin-left:5px;vertical-align:1px}
.badge.panel{background:var(--accent-tint);color:var(--accent-soft)}
.badge.ok{background:var(--ok-bg);color:var(--ok)}
.badge.unknown{background:var(--warn-bg);color:var(--warn)}
.badge.dupe{background:var(--inset);color:var(--muted)}
.detail-link{font-size:12px;color:var(--accent);cursor:pointer;margin-left:6px;vertical-align:1px;font-weight:500;white-space:nowrap}
.detail-link:hover{text-decoration:underline}
.copy-link{color:var(--accent);cursor:pointer}
.copy-link:hover{text-decoration:underline}
.linkrow{justify-content:space-between;align-items:center}
.linkrow .group{display:flex;gap:8px;flex-wrap:wrap}
.btn.import{background:var(--text);border-color:var(--text);color:var(--bg);border-radius:999px;padding:10px 18px;font-weight:600;display:inline-flex;align-items:center;gap:6px}
.linkrow a.btn.import{color:var(--bg)}
.btn.ghost{background:transparent;border:1px solid var(--line-strong);color:var(--text);border-radius:999px;padding:10px 16px;display:inline-flex;align-items:center;gap:6px}
.btn.ghost:hover{border-color:var(--accent)}
.star{position:absolute;top:12px;right:10px;border:none;background:none;font-size:19px;cursor:pointer;color:var(--faint);padding:2px 6px}
.star.fav{color:var(--star)}
.src-links{margin-top:10px;font-size:12.5px;display:flex;gap:14px}
.src-links a{color:var(--accent);text-decoration:none}
.src-links a:hover{text-decoration:underline}
.src-links a.btn.import:hover{text-decoration:none}
.more{display:block;width:100%;margin:16px 0 8px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);font-size:15px;cursor:pointer}
footer{color:var(--faint);font-size:12.5px;text-align:center;padding:18px 12px 28px;line-height:1.7}
.about{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;text-align:left;max-width:1060px;margin:0 auto 14px;color:var(--muted)}
.about b{font-size:14px;color:var(--text)}
.about a{color:var(--accent);text-decoration:none}
.about a:hover{text-decoration:underline}
.modal-bg{position:fixed;inset:0;background:var(--scrim);z-index:50;display:none;align-items:flex-end;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:var(--card);width:100%;max-width:720px;max-height:88vh;overflow-y:auto;border-radius:16px 16px 0 0;padding:18px 16px calc(20px + env(safe-area-inset-bottom))}
.modal h2{font-size:19px;font-weight:700;letter-spacing:-.01em;padding-right:60px;margin-top:4px}
.modal .meta{margin-top:6px}
.modal .desc-full{font-size:14.5px;margin-top:12px;white-space:pre-wrap;word-break:break-word;color:var(--muted);line-height:1.7}
.kv{margin-top:12px;font-size:13.5px}
.kv div{padding:5px 0;border-bottom:1px solid var(--line);word-break:break-all}
.kv span{color:var(--faint)}
.kv a{color:var(--accent);text-decoration:none}
.linkrow{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.linkrow .btn{padding:10px 14px}
.linkrow a.btn{text-decoration:none;color:var(--text);display:inline-block}
.hint{background:var(--inset);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px;color:var(--muted);margin-top:12px;line-height:1.7}
.tabs{display:flex;gap:8px;margin-top:16px}
.tabs .btn.on{background:var(--accent);border-color:var(--accent);color:var(--accent-fg)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-fg)}
.linkrow a.btn.primary{color:var(--accent-fg)}
.btn.disabled{background:var(--inset);border-color:var(--line);color:var(--faint);cursor:not-allowed}
.preview-summary{display:flex;flex-wrap:wrap;gap:6px 14px;background:var(--inset);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:12.5px;color:var(--muted);margin-top:10px}
.preview-summary b{color:var(--text)}
.raw .sec{color:var(--ok);font-weight:700}
.raw .com{color:var(--faint)}
pre.raw{background:var(--inset);color:var(--text);border-radius:10px;padding:12px;font-size:12px;overflow:auto;max-height:50vh;white-space:pre;margin-top:10px}
.close{position:absolute;top:12px;right:12px}
body{padding-bottom:92px}
.glow-field{position:absolute;left:0;right:0;top:0;height:520px;pointer-events:none;background-image:radial-gradient(58% 55% at 50% 0%,rgb(139 156 255/.16),transparent 72%)}
[data-theme="light"] .glow-field{background-image:radial-gradient(58% 55% at 50% 0%,rgb(101 120 232/.1),transparent 72%)}
.hero{position:relative;overflow:hidden}
.hero-in{position:relative;display:grid;grid-template-columns:1fr}
.hero-intro{display:flex;flex-direction:column;align-items:center;text-align:center;padding:56px 6px 0}
.hero-badge{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:6px 12px;font-size:11.5px;color:var(--muted)}
.hero-badge .dot{width:6px;height:6px;border-radius:50%;background:var(--ok)}
.hero h1{font-size:clamp(37px,9vw,54px);font-weight:600;line-height:1.05;letter-spacing:-.032em;margin-top:24px;max-width:19ch}
.hero h1 .grad{display:block;background:linear-gradient(180deg,var(--text),var(--accent-soft));-webkit-background-clip:text;background-clip:text;color:transparent}
.hero-sub{color:var(--muted);font-size:15px;margin-top:20px;line-height:1.72;max-width:46ch}
.hero-actions{display:flex;flex-direction:column;gap:10px;width:100%;margin-top:32px}
.btn-hero-pri{background:var(--accent);color:var(--accent-fg);border:1px solid var(--accent);border-radius:999px;padding:13px 22px;font-size:15px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-family:inherit}
.btn-hero-sec{background:transparent;color:var(--text);border:1px solid var(--line-strong);border-radius:999px;padding:13px 22px;font-size:15px;font-weight:600;cursor:pointer;font-family:inherit}
.btn-hero-sec:hover{border-color:var(--accent)}
.statgrid{position:relative;display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:48px 6px 0}
.statcard{position:relative;background:var(--glass-bg);-webkit-backdrop-filter:blur(20px) saturate(160%);backdrop-filter:blur(20px) saturate(160%);border:1px solid var(--glass-line);border-radius:16px;padding:16px;text-align:left;cursor:pointer;font-family:inherit;color:var(--text);box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-sm);transition:transform .2s,border-color .2s,box-shadow .2s,background .2s}
.statcard:hover{transform:translateY(-2px);border-color:var(--glass-hi);background:color-mix(in srgb,var(--glass-bg) 82%,#fff 18%);box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-md)}
.stat-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.stat-label{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.stat-top svg{color:var(--faint);flex:0 0 auto}
.statcard:hover .stat-top svg{color:var(--accent)}
.stat-value{display:block;margin-top:10px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:21px;font-weight:500;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stat-hint{display:block;margin-top:6px;font-size:10.5px;color:var(--faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hero-foot{position:relative;text-align:center;font-size:10.5px;color:var(--faint);padding:32px 6px}
@media(min-width:640px){.hero-actions{flex-direction:row;width:auto}}
@media(min-width:1024px){
.hero-in{grid-template-columns:5fr 7fr;gap:40px;align-items:center;padding:64px 0 80px}
.hero-intro{align-items:flex-start;text-align:left;padding:0}
.hero h1{font-size:clamp(48px,4.5vw,62px)}
.hero-sub{font-size:16px}
.statgrid{padding:0}
.stat-value{font-size:26px}
.hero-foot{padding:0 6px 40px}
}
.home-sec{padding-top:48px}
.band{margin:48px -12px 0;padding:48px 16px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--surface);background:color-mix(in srgb,var(--surface) 40%,transparent)}
.band-top{margin:48px -12px 0;padding:48px 16px 56px;border-top:1px solid var(--line);background:var(--surface);background:color-mix(in srgb,var(--surface) 40%,transparent)}
.sec-head{display:flex;flex-direction:column;gap:20px}
@media(min-width:640px){.sec-head{flex-direction:row;align-items:flex-end;justify-content:space-between}}
.eyebrow{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.eyebrow .idx{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;color:var(--faint);letter-spacing:0}
.sec-title{font-size:24px;font-weight:600;letter-spacing:-.02em;line-height:1.14;margin-top:10px}
@media(min-width:640px){.sec-title{font-size:30px}}
.sec-sub{color:var(--muted);font-size:13.5px;margin-top:10px;line-height:1.6;max-width:560px}
@media(min-width:640px){.sec-sub{font-size:14.5px}}
.sec-action{flex:0 0 auto;font-size:13px;color:var(--muted);text-decoration:none;display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.sec-action:hover{color:var(--text)}
.sec-link{display:inline-block;color:var(--accent);font-size:13px;font-weight:600;margin:0 0 16px;text-decoration:none}
.empty-state{text-align:center;padding:32px 0 8px}
.empty-state b{font-size:15px;font-weight:600}
.empty-state p{color:var(--muted);font-size:13.5px;margin:8px 0 16px}
.cat-note{margin-top:20px;font-size:11px;color:var(--faint);line-height:1.6}
.cat-note a{color:var(--muted);margin-left:8px;text-decoration:none}
.cat-note a:hover{text-decoration:underline;color:var(--text)}
#homeUpd{margin-top:28px}
#homeLib{margin-top:28px}
.lib-sec{border-top:1px solid var(--line)}
.lib-foot{display:flex;flex-direction:column;align-items:flex-start;gap:16px;border-top:1px solid var(--line);margin-top:32px;padding-top:24px}
.lib-foot p{font-size:11.5px;color:var(--faint);line-height:1.7}
@media(min-width:640px){.lib-foot{flex-direction:row;align-items:center;justify-content:space-between}}
.plat-grid{display:grid;grid-template-columns:1fr;gap:40px}
@media(min-width:1024px){.plat-grid{grid-template-columns:320px minmax(0,1fr);gap:64px}}
.plat-intro .sec-link{margin-top:20px}
.plat-cards{display:grid;grid-template-columns:1fr;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:20px;overflow:hidden}
@media(min-width:640px){.plat-cards{grid-template-columns:1fr 1fr}}
.plat-cell{background:var(--card);padding:20px}
.plat-cell b{font-size:13.5px;font-weight:600}
.plat-cell p{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.7}
.catgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
.catcard{position:relative;background:var(--glass-bg);-webkit-backdrop-filter:blur(20px) saturate(160%);backdrop-filter:blur(20px) saturate(160%);border:1px solid var(--glass-line);border-radius:18px;padding:16px;cursor:pointer;box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-sm);transition:transform .2s,box-shadow .2s,border-color .2s,background .2s}
.catcard:hover{border-color:var(--glass-hi);background:color-mix(in srgb,var(--glass-bg) 82%,#fff 18%);transform:translateY(-2px);box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-md)}
.cat-eyebrow{font-size:12px;color:var(--faint);margin-bottom:8px}
.cat-eyebrow span{color:var(--muted)}
.catcard h4{font-size:16px;font-weight:600;letter-spacing:-.01em}
.catcard h4 .ver{font-size:12px;color:var(--faint);font-weight:400;margin-left:6px}
.cat-desc{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.catcard .tags{margin-top:8px}
.catcard .go{font-size:12.5px;color:var(--accent);margin-top:10px}
.nav{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(14px + env(safe-area-inset-bottom));z-index:40;display:flex;width:min(480px,calc(100% - 24px));background:var(--glass-bg);-webkit-backdrop-filter:blur(28px) saturate(180%) brightness(1.12);backdrop-filter:blur(28px) saturate(180%) brightness(1.12);border:1px solid var(--glass-line);border-radius:999px;padding:6px 8px;box-shadow:inset 0 1px 0 var(--glass-hi),inset 0 -1px 0 rgba(255,255,255,.06),0 12px 32px rgba(0,0,0,.35),0 2px 8px rgba(0,0,0,.22)}
.nav::before{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(180deg,rgba(255,255,255,.14),rgba(255,255,255,.02) 45%,transparent 60%);pointer-events:none}
.nav button{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;background:none;border:none;color:var(--muted);font-size:12px;padding:6px 0 5px;cursor:pointer;position:relative;font-family:inherit;border-radius:999px;transition:background .2s,color .2s}
.nav button svg{display:block}
.nav button.on{color:var(--accent);background:var(--accent-tint)}
.upd-list{display:flex;flex-direction:column;gap:8px;margin-top:12px}
.upd-row{position:relative;background:var(--glass-bg);-webkit-backdrop-filter:blur(20px) saturate(160%);backdrop-filter:blur(20px) saturate(160%);border:1px solid var(--glass-line);border-radius:16px;padding:13px 14px;cursor:pointer;box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-sm);transition:transform .2s,box-shadow .2s,border-color .2s,background .2s}
.upd-row:hover{border-color:var(--glass-hi);background:color-mix(in srgb,var(--glass-bg) 82%,#fff 18%);transform:translateY(-2px);box-shadow:inset 0 1px 0 var(--glass-hi),var(--shadow-md)}
.upd-top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.upd-name{font-size:16px;font-weight:600}
.upd-time{margin-left:auto;font-size:12.5px;color:var(--faint);white-space:nowrap}
.upd-desc{font-size:13px;color:var(--muted);margin-top:4px;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
@media(min-width:700px){.modal-bg{align-items:center;padding:20px}.modal{border-radius:16px}}
</style>
</head>
<body>
<header>
  <div class="header-in">
    <div class="brand"><img class="logo" src="data:image/png;base64,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" alt="Surge Modules"><h1>Surge Modules</h1></div>
    <nav class="topnav" id="topNav" aria-label="主导航">
      <button data-nav="home" class="on">首页</button>
      <button data-nav="discover">发现</button>
      <button data-nav="fav">收藏</button>
      <button data-nav="updates">更新</button>
    </nav>
    <button class="theme-btn" id="themeBtn" aria-label="切换主题"></button>
  </div>
</header>
<main>
  <section id="view-home">
    <div class="hero">
      <div class="glow-field" aria-hidden="true"></div>
      <div class="hero-in">
        <div class="hero-intro">
          <span class="hero-badge"><span class="dot"></span>独立 Surge 模块索引</span>
          <h1>让 Surge 模块<span class="grad">发现更简单</span></h1>
          <p class="hero-sub">浏览、搜索与收藏优质 Surge 模块，查看版本记录、复制安装链接，一次找到需要的规则与脚本。</p>
          <div class="hero-actions">
            <button class="btn-hero-pri" onclick="showView('discover')">探索模块 <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg></button>
            <button class="btn-hero-sec" onclick="showView('discover')">浏览分类</button>
          </div>
        </div>
        <div class="statgrid">
          <button class="statcard" onclick="showView('discover')">
            <span class="stat-top"><span class="stat-label">模块总数</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg></span>
            <span class="stat-value">__TOTAL__</span>
            <span class="stat-hint">已收录并公开</span>
          </button>
          <button class="statcard" onclick="showView('discover')">
            <span class="stat-top"><span class="stat-label">分类</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275Z"/></svg></span>
            <span class="stat-value">__CATS__</span>
            <span class="stat-hint">最多：__TOPCAT__</span>
          </button>
          <button class="statcard" onclick="showView('discover')">
            <span class="stat-top"><span class="stat-label">模块来源</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></span>
            <span class="stat-value">__SOURCES__</span>
            <span class="stat-hint">已接入的上游仓库</span>
          </button>
          <button class="statcard" onclick="showView('updates')">
            <span class="stat-top"><span class="stat-label">最近更新</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></span>
            <span class="stat-value">__LASTUPD_DOTS__</span>
            <span class="stat-hint">__TOTAL__ 个版本记录</span>
          </button>
        </div>
      </div>
      <p class="hero-foot">模块数据构建时生成，共 __TOTAL__ 个模块</p>
    </div>
    <section class="band">
      <div class="sec-head">
        <div>
          <div class="eyebrow">精选 <span class="idx">02</span></div>
          <h2 class="sec-title">本期推荐</h2>
          <p class="sec-sub">每个分类各取一个最近更新的可用模块。</p>
        </div>
        <a class="sec-action" href="#discover" onclick="showView('discover');return false;">全部模块 ↗</a>
      </div>
      <div class="grid" id="featGrid"></div>
    </section>
    <section class="home-sec">
      <div class="sec-head">
        <div>
          <div class="eyebrow">分类 <span class="idx">01</span></div>
          <h2 class="sec-title">按用途浏览</h2>
          <p class="sec-sub">从拦截规则到脚本增强，按实际用途归类的模块目录。</p>
        </div>
        <a class="sec-action" href="#discover" onclick="showView('discover');return false;">参与筛选 ↗</a>
      </div>
      <div class="catgrid" id="catGrid"></div>
      <p class="cat-note">数据随构建更新。<a href="#discover" onclick="showView('discover');return false;">查看全部模块</a></p>
    </section>
    <section class="home-sec">
      <div class="sec-head">
        <div>
          <div class="eyebrow">更新 <span class="idx">03</span></div>
          <h2 class="sec-title">最近更新</h2>
          <p class="sec-sub">按发布倒序排列的模块版本记录。</p>
        </div>
        <a class="sec-action" href="#updates" onclick="showView('updates');return false;">查看全部更新 ↗</a>
      </div>
      <div class="upd-list" id="homeUpd"></div>
    </section>
    <section class="home-sec lib-sec">
      <div class="sec-head">
        <div>
          <div class="eyebrow">模块库 <span class="idx">04</span></div>
          <h2 class="sec-title">全部模块</h2>
          <p class="sec-sub">当前索引 __TOTAL__ 个已发布模块，按更新时间倒序展示。</p>
        </div>
        <a class="sec-action" href="#discover" onclick="showView('discover');return false;">探索全部模块 ↗</a>
      </div>
      <div class="grid" id="homeLib"></div>
      <div class="lib-foot"><p>展示的是索引内的全部内容，不含安装量或热度排序</p><button class="btn" style="padding:10px 18px" onclick="showView('discover')">进入发现页 →</button></div>
    </section>
    <section class="band-top">
      <div class="plat-grid">
        <div class="plat-intro">
          <div class="eyebrow">关于平台 <span class="idx">05</span></div>
          <h2 class="sec-title">一个专注的模块索引。</h2>
          <p class="sec-sub">不做社区，不做商店。只负责把模块整理清楚，让你更快找到需要的那一个。</p>
          <a class="sec-link" href="#aboutBox">了解平台范围 ↗</a>
        </div>
        <div class="plat-cards">
          <div class="plat-cell"><b>独立索引</b><p>由维护者整理的 Surge 模块目录，与 Surge 官方无隶属关系。</p></div>
          <div class="plat-cell"><b>安装链接</b><p>一键复制安装链接，或直接唤起 Surge 添加模块。</p></div>
          <div class="plat-cell"><b>版本记录</b><p>记录每个模块的版本号、发布时间与更新说明。</p></div>
          <div class="plat-cell"><b>本地收藏</b><p>收藏保存在本机浏览器，无需账号，清除站点数据会一并清空。</p></div>
        </div>
      </div>
    </section>
  </section>
  <section id="view-discover" style="display:none">
    <div class="sub-head">
      <div class="eyebrow">发现</div>
      <h1>模块目录</h1>
      <p>按分类、标签与关键词筛选，快速定位需要的模块。</p>
    </div>
    <div class="disc-tools">
      <div class="searchrow">
        <input id="q" type="search" placeholder="搜索模块、描述、作者或标签…" autocomplete="off">
      </div>
      <div class="disc-tools-row">
        <button class="btn" id="filterBtn">筛选 <span class="filter-dot" id="filterDot" style="display:none"></span></button>
        <div class="sortseg" role="group" aria-label="排序方式">
          <button data-sort="rec" class="on">推荐</button>
          <button data-sort="updated">最近更新</button>
          <button data-sort="name">名称</button>
        </div>
      </div>
    </div>
    <div class="filter-panel" id="filterPanel" style="display:none">
      <div class="fp-head"><b>资源筛选</b><button class="fp-close" id="filterClose" aria-label="收起筛选">✕</button></div>
      <div class="fp-grid">
        <div class="fp-sec"><p class="fp-label">来源（<span id="srcCount"></span>）</p><div class="fchips" id="srcChips"></div></div>
        <div class="fp-sec"><p class="fp-label">分类（<span id="catCount2"></span>）</p><div class="fchips" id="catChips"></div></div>
        <div class="fp-sec"><p class="fp-label">功能</p><div class="fchips" id="featChips"></div></div>
        <div class="fp-sec"><p class="fp-label">标签</p><div class="fchips" id="tagChips"></div></div>
      </div>
      <button class="fp-reset" id="filterReset" style="display:none">重置筛选 ✕</button>
    </div>
    <div class="active-filters" id="activeFilters" style="display:none"></div>
    <p class="res-count" id="count"></p>
    <div class="grid" id="grid"></div>
    <div class="empty-state" id="empty" style="display:none"><b>没有符合条件的模块</b><p>换一个关键词，或清除筛选条件重新浏览。</p><button class="btn" style="padding:10px 18px" id="clearFilters">清除筛选</button></div>
    <div class="pager" id="pager" style="display:none">
      <button id="pagePrev" aria-label="上一页">‹</button>
      <span id="pageInfo"></span>
      <button id="pageNext" aria-label="下一页">›</button>
    </div>
    <section class="disc-cats">
      <h2>分类</h2>
      <p class="sec-sub">选择一个分类快速缩小范围。</p>
      <div class="catgrid" id="discCatGrid" style="margin-top:20px"></div>
      <div style="margin-top:24px"><button class="btn ghost" onclick="showView('home')">返回首页</button></div>
    </section>
  </section>
  <section id="view-fav" style="display:none">
    <div class="sub-head">
      <div class="eyebrow">收藏</div>
      <h1>我的收藏</h1>
      <p>收藏保存在这台设备的浏览器中，刷新或重新打开都不会丢失。</p>
    </div>
    <p class="fav-count-line" id="favCount" style="display:none"></p>
    <div class="grid" id="favGrid"></div>
    <div class="empty-state" id="favEmpty" style="display:none"><b>还没有收藏任何模块</b><p>在模块卡片或详情页点击收藏，之后可以在这里集中查看。收藏只保存在本机，不会上传。</p><button class="btn" style="padding:10px 18px" onclick="showView('discover')">去发现模块</button></div>
    <p class="fav-note">账号体系与云端同步尚未实现；当前收藏不会跨设备同步，清除站点数据会一并清空。</p>
  </section>
  <section id="view-updates" style="display:none">
    <div class="sub-head">
      <div class="eyebrow">更新</div>
      <h1>更新日志</h1>
      <p>平台公告与模块版本记录。</p>
    </div>
    <div class="upd-layout">
      <section class="upd-main">
        <div class="upd-sec-head"><h2>模块更新</h2><span id="updCount"></span></div>
        <div id="updGroups"></div>
        <div class="empty-state" id="updEmpty" style="display:none"><b>暂无模块更新</b><p>模块同步并发布新版本后，记录会出现在这里。</p><button class="btn" style="padding:10px 18px" id="updReload">重新加载</button></div>
        <button class="more" id="updMore">加载更多</button>
      </section>
      <aside class="upd-side">
        <div class="upd-sec-head"><h2>平台公告</h2></div>
        <div class="ann-empty"><p>暂无公告</p></div>
      </aside>
    </div>
  </section>
</main>
<nav class="nav" id="bottomNav">
  <button data-nav="home" class="on"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>首页</button>
  <button data-nav="discover"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>发现</button>
  <button data-nav="fav"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>收藏</button>
  <button data-nav="updates"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>更新</button>
</nav>
<footer>
  <div class="about" id="aboutBox">
    <b>数据来源与说明</b><br>
    本站数据来自 <a href="https://son.zhiaon.top" target="_blank" rel="noopener">son.zhiaon.top</a>（许舟的 Surge Modules 索引），本站为独立镜像 / 索引站，定期从上游同步；与 Surge 官方无关。<br>
    数据更新至：__UPDATED_AT__ · 数据快照：__GENERATED_AT__<br>
    全部模块版权归原作者所有，作者与仓库链接均保留在每条记录中；本站不声称拥有任何模块。
  </div>
  模块文件均可在本站 /m/ 目录下查看原文。
</footer>
<div class="modal-bg" id="modalBg">
  <div class="modal" id="modal"></div>
</div>
<script>
var MODULES = __MODULES_JSON__;
var PAGE = 60;
var FAV_KEY = 'surge-modules-favs-v1';
var favs = {};
try { JSON.parse(localStorage.getItem(FAV_KEY) || '[]').forEach(function(s){ favs[s] = 1; }); } catch(e) {}
function saveFavs(){ try { localStorage.setItem(FAV_KEY, JSON.stringify(Object.keys(favs))); } catch(e) {} }
var FAV_ADDED_KEY = 'surge-modules-favs-added-v1';
var favAdded = {};
try { favAdded = JSON.parse(localStorage.getItem(FAV_ADDED_KEY) || '{}') || {}; } catch(e) { favAdded = {}; }
function saveFavAdded(){ try { localStorage.setItem(FAV_ADDED_KEY, JSON.stringify(favAdded)); } catch(e) {} }
var state = { q:'', cat:'all', tag:'', sort:'rec', page:1, owner:'', panelOnly:false };
var PAGE_SIZE = 24;
var BASE_URL = location.protocol.indexOf('http') === 0 ? location.origin : '';
function surgeInstallUrl(m){ return 'surge:///install-module?url=' + encodeURIComponent(BASE_URL + m.url); }
var ICO_DOWN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m6 11 6 6 6-6"/><path d="M4 21h16"/></svg>';
var ICO_LINK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>';
var ICO_CFG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>';

function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function fmtDate(s){ return s ? String(s).slice(0, 10) : ''; }
function relTime(s){
  if (!s) return '';
  var t = Date.parse(s); if (isNaN(t)) return fmtDate(s);
  var d = Date.now() - t;
  if (d < 0) return fmtDate(s);
  var m = Math.floor(d / 60000);
  if (m < 1) return '刚刚';
  if (m < 60) return m + '分钟前';
  var h = Math.floor(m / 60);
  if (h < 24) return h + '小时前';
  var days = Math.floor(h / 24);
  if (days < 30) return days + '天前';
  return fmtDate(s);
}

var catCounts = {}, tagCounts = {};
MODULES.forEach(function(m){
  var c = (m.category && m.category.name) || '未分类';
  catCounts[c] = (catCounts[c] || 0) + 1;
  (m.tags || []).forEach(function(t){ tagCounts[t] = (tagCounts[t] || 0) + 1; });
});
var CATS = Object.keys(catCounts).sort(function(a, b){ return catCounts[b] - catCounts[a]; });
var TOP_TAGS = Object.keys(tagCounts).sort(function(a, b){ return tagCounts[b] - tagCounts[a]; }).slice(0, 14);
var ownerCounts = {}, ownerRepo = {};
MODULES.forEach(function(m){
  var u = (m.repositoryUrl || '').replace(/\/$/, '');
  if (u.indexOf('github.com') === -1) return;
  var parts = u.replace(/^https?:\/\/github\.com\//i, '').split('/');
  if (parts.length < 2) return;
  var key = (parts[0] + '/' + parts[1]).toLowerCase();
  ownerCounts[key] = (ownerCounts[key] || 0) + 1;
  ownerRepo[key] = parts[0];
});
var SOURCES = Object.keys(ownerCounts).sort(function(a, b){ return ownerCounts[b] - ownerCounts[a]; });
var panelCount = MODULES.filter(function(m){ return m.hasPanel; }).length;

function hasFilters(){
  return Boolean(state.owner || state.cat !== 'all' || state.tag || state.panelOnly || state.sort !== 'rec' || state.q);
}
function afChip(label, key){
  return '<span class="af-chip">' + label + '<button data-af="' + key + '" aria-label="移除这个筛选条件">✕</button></span>';
}
function renderActive(){
  var bar = document.getElementById('activeFilters');
  if (!hasFilters()) { bar.style.display = 'none'; bar.innerHTML = ''; return; }
  var h = '<span class="af-label">当前筛选</span>';
  if (state.owner) h += afChip('来源：' + esc(state.owner), 'owner');
  if (state.cat !== 'all') h += afChip(esc(state.cat), 'cat');
  if (state.tag) h += afChip('#' + esc(state.tag), 'tag');
  if (state.panelOnly) h += afChip('含面板 [Panel]', 'panel');
  if (state.sort !== 'rec') h += afChip('排序：' + (state.sort === 'updated' ? '最近更新' : '名称'), 'sort');
  if (state.q) h += afChip('“' + esc(state.q) + '”', 'q');
  h += '<button class="af-clear" id="afClearAll">清除全部</button>';
  bar.innerHTML = h;
  bar.style.display = 'flex';
}
function renderPanel(){
  var h = '<span class="fchip' + (!state.owner ? ' on' : '') + '" data-owner="">全部</span>';
  SOURCES.forEach(function(k){
    h += '<span class="fchip' + (state.owner === k ? ' on' : '') + '" data-owner="' + esc(k) + '"><img src="https://github.com/' + esc(ownerRepo[k]) + '.png?size=48" alt="" loading="lazy" onerror="this.style.display=\'none\'">' + esc(ownerRepo[k]) + '<small>' + ownerCounts[k] + '</small></span>';
  });
  document.getElementById('srcChips').innerHTML = h;
  document.getElementById('srcCount').textContent = SOURCES.length;
  var c = '<span class="fchip' + (state.cat === 'all' ? ' on' : '') + '" data-cat2="all">全部</span>';
  CATS.forEach(function(n){
    c += '<span class="fchip' + (state.cat === n ? ' on' : '') + '" data-cat2="' + esc(n) + '">' + esc(n) + '<small>' + catCounts[n] + '</small></span>';
  });
  document.getElementById('catChips').innerHTML = c;
  document.getElementById('catCount2').textContent = CATS.length;
  document.getElementById('featChips').innerHTML =
    '<span class="fchip' + (!state.panelOnly ? ' on' : '') + '" data-feat="all">全部</span>' +
    '<span class="fchip' + (state.panelOnly ? ' on' : '') + '" data-feat="panel">含面板<small>' + panelCount + '</small></span>';
  var t = '<span class="fchip' + (!state.tag ? ' on' : '') + '" data-tag2="all">全部</span>';
  TOP_TAGS.forEach(function(n){
    t += '<span class="fchip' + (state.tag === n ? ' on' : '') + '" data-tag2="' + esc(n) + '">' + esc(n) + '<small>' + tagCounts[n] + '</small></span>';
  });
  document.getElementById('tagChips').innerHTML = t;
  document.getElementById('filterDot').style.display = hasFilters() ? 'inline-block' : 'none';
  document.getElementById('filterReset').style.display = (state.owner || state.cat !== 'all' || state.tag || state.panelOnly) ? 'inline' : 'none';
  renderActive();
}
document.getElementById('filterPanel').addEventListener('click', function(e){
  var o = e.target.closest('[data-owner]');
  if (o) { var v = o.getAttribute('data-owner'); state.owner = (state.owner === v) ? '' : v; state.page = 1; renderPanel(); render(); return; }
  var c = e.target.closest('[data-cat2]');
  if (c) { state.cat = c.getAttribute('data-cat2'); state.page = 1; renderPanel(); render(); return; }
  var f = e.target.closest('[data-feat]');
  if (f) { state.panelOnly = f.getAttribute('data-feat') === 'panel' ? !state.panelOnly : false; state.page = 1; renderPanel(); render(); return; }
  var t = e.target.closest('[data-tag2]');
  if (t) { var tv = t.getAttribute('data-tag2'); state.tag = (tv === 'all' || state.tag === tv) ? '' : tv; state.page = 1; renderPanel(); render(); return; }
});
document.getElementById('filterReset').addEventListener('click', function(){
  state.owner = ''; state.cat = 'all'; state.tag = ''; state.panelOnly = false; state.page = 1; renderPanel(); render();
});
document.getElementById('filterBtn').addEventListener('click', function(){
  var p = document.getElementById('filterPanel');
  p.style.display = p.style.display === 'none' ? 'block' : 'none';
});
document.getElementById('filterClose').addEventListener('click', function(){
  document.getElementById('filterPanel').style.display = 'none';
});
document.getElementById('activeFilters').addEventListener('click', function(e){
  if (e.target.id === 'afClearAll') {
    state.q = ''; document.getElementById('q').value = '';
    state.owner = ''; state.cat = 'all'; state.tag = ''; state.panelOnly = false; state.sort = 'rec'; state.page = 1;
    document.querySelectorAll('.sortseg button').forEach(function(x){ x.classList.toggle('on', x.getAttribute('data-sort') === 'rec'); });
    renderPanel(); render(); return;
  }
  var b = e.target.closest('[data-af]'); if (!b) return;
  var k = b.getAttribute('data-af');
  if (k === 'owner') state.owner = '';
  else if (k === 'cat') state.cat = 'all';
  else if (k === 'tag') state.tag = '';
  else if (k === 'panel') state.panelOnly = false;
  else if (k === 'sort') { state.sort = 'rec'; document.querySelectorAll('.sortseg button').forEach(function(x){ x.classList.toggle('on', x.getAttribute('data-sort') === 'rec'); }); }
  else if (k === 'q') { state.q = ''; document.getElementById('q').value = ''; }
  state.page = 1; renderPanel(); render();
});
document.getElementById('clearFilters').addEventListener('click', function(){
  state.q = ''; document.getElementById('q').value = '';
  state.owner = ''; state.cat = 'all'; state.tag = ''; state.panelOnly = false; state.sort = 'rec'; state.page = 1;
  document.querySelectorAll('.sortseg button').forEach(function(x){ x.classList.toggle('on', x.getAttribute('data-sort') === 'rec'); });
  renderPanel(); render();
});
document.querySelector('.sortseg').addEventListener('click', function(e){
  var b = e.target.closest('[data-sort]'); if (!b) return;
  state.sort = b.getAttribute('data-sort'); state.page = 1;
  document.querySelectorAll('.sortseg button').forEach(function(x){ x.classList.toggle('on', x === b); });
  renderPanel(); render();
});
document.getElementById('pagePrev').addEventListener('click', function(){
  if (state.page <= 1) return;
  state.page--; render();
  document.getElementById('grid').scrollIntoView();
});
document.getElementById('pageNext').addEventListener('click', function(){
  state.page++; render();
  document.getElementById('grid').scrollIntoView();
});

function matches(m, q){
  if (!q) return true;
  var hay = [m.name, m.author, (m.tags || []).join(' '), m.description,
             (m.py && m.py.full) || '', (m.py && m.py.initials) || ''].join(' ').toLowerCase();
  return q.toLowerCase().split(/\s+/).every(function(t){ return t && hay.indexOf(t) !== -1; });
}
function filtered(){
  var list = MODULES.filter(function(m){
    if (state.owner && (m.repositoryUrl || '').toLowerCase().indexOf(state.owner.toLowerCase()) === -1) return false;
    if (state.panelOnly && !m.hasPanel) return false;
    if (state.cat !== 'all' && ((m.category && m.category.name) || '未分类') !== state.cat) return false;
    if (state.tag && (m.tags || []).indexOf(state.tag) === -1) return false;
    return matches(m, state.q);
  });
  if (state.sort === 'name') list.sort(function(a, b){ return String(a.name).localeCompare(String(b.name), 'zh'); });
  else if (state.sort === 'rec') list.sort(function(a, b){ return ((b.health === 'ok' ? 1 : 0) - (a.health === 'ok' ? 1 : 0)) || String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  else list.sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  return list;
}
function cardHtml(m, rel){
  var health = m.health === 'ok' ? '<span class="badge ok">可用</span>' : '<span class="badge unknown">未检测</span>';
  var panel = m.hasPanel ? '<span class="badge panel">面板</span>' : '';
  var dupe = (m.dupe > 0) ? '<span class="badge dupe">同名 ' + m.dupe + '</span>' : '';
  var tags = (m.tags || []).slice(0, 4).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('');
  var links = '';
  if (BASE_URL) links += '<a class="btn import" href="' + surgeInstallUrl(m) + '">导入 Surge</a>';
  var isNew = m.updatedAt && (Date.now() - new Date(m.updatedAt).getTime() < 7*24*3600*1000);
  return '<article class="card' + (isNew ? ' is-new' : '') + '" data-slug="' + esc(m.slug) + '">' +
    '<button class="star' + (favs[m.slug] ? ' fav' : '') + '" data-star="' + esc(m.slug) + '" aria-label="收藏">' + (favs[m.slug] ? '★' : '☆') + '</button>' +
    '<div class="card-top"><span class="cat">' + esc((m.category && m.category.name) || '未分类') + '</span><span class="ver">' + esc(m.version || '') + '</span>' + health + '</div>' +
    '<h3>' + esc(m.name) + panel + dupe + '</h3>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + (rel ? ' · ' + esc(rel) : '') + '</div>' +
    '<div class="desc">' + esc(m.description || '') + '</div>' +
    '<div class="tags">' + tags + '</div>' +
    '<div class="src-links">' + links + '</div></article>';
}
function render(){
  var list = filtered();
  var totalPages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
  if (state.page > totalPages) state.page = totalPages;
  document.getElementById('count').textContent = '共 ' + list.length + ' 个模块';
  document.getElementById('empty').style.display = list.length ? 'none' : 'block';
  document.getElementById('grid').innerHTML = list.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE).map(cardHtml).join('');
  document.getElementById('pager').style.display = list.length > PAGE_SIZE ? 'flex' : 'none';
  document.getElementById('pagePrev').disabled = state.page <= 1;
  document.getElementById('pageNext').disabled = state.page >= totalPages;
  document.getElementById('pageInfo').textContent = state.page + ' / ' + totalPages;
}
function onGridClick(e){
  if (e.target.closest('a')) return; // 卡片内的仓库 / 上游原文链接：直接跳转，不打开详情
  var cp = e.target.closest('[data-copy]');
  if (cp) { copyText(cp.getAttribute('data-copy'), cp); return; }
  var star = e.target.closest('[data-star]');
  if (star) {
    e.stopPropagation();
    var slug = star.getAttribute('data-star');
    if (favs[slug]) { delete favs[slug]; delete favAdded[slug]; }
    else { favs[slug] = 1; favAdded[slug] = new Date().toISOString(); }
    saveFavs(); saveFavAdded(); refreshCurrentView(); return;
  }
  var card = e.target.closest('[data-slug]');
  if (card) openDetail(card.getAttribute('data-slug'));
}
['grid','favGrid','updGroups','homeUpd','homeLib','featGrid'].forEach(function(id){ document.getElementById(id).addEventListener('click', onGridClick); });
var qTimer = null;
document.getElementById('q').addEventListener('input', function(e){
  clearTimeout(qTimer);
  qTimer = setTimeout(function(){ state.q = e.target.value.trim(); state.page = 1; renderPanel(); render(); }, 150);
});

function installUrl(m){
  if (location.protocol.indexOf('http') === 0) return location.origin + m.url;
  return m.url;
}
function copyText(t, btn){
  function done(){ if (btn) { var o = btn.innerHTML; btn.innerHTML = '已复制 ✓'; setTimeout(function(){ btn.innerHTML = o; }, 1500); } }
  if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(t).then(done, function(){ fallback(); }); }
  else fallback();
  function fallback(){
    var ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta);
    ta.select(); try { document.execCommand('copy'); done(); } catch(e) {} document.body.removeChild(ta);
  }
}
var currentSlug = null;
function openDetail(slug){
  var m = null;
  MODULES.forEach(function(x){ if (x.slug === slug) m = x; });
  if (!m) return;
  currentSlug = slug;
  var url = installUrl(m);
  var repo = m.repositoryUrl ? '<div><span>仓库：</span><a href="' + esc(m.repositoryUrl) + '" target="_blank" rel="noopener">' + esc(m.repositoryUrl) + '</a></div>' : '';
  var up = m.upstreamUrl ? '<div><span>上游原文：</span><a href="' + esc(m.upstreamUrl) + '" target="_blank" rel="noopener">' + esc(m.upstreamUrl) + '</a></div>' : '';
  var same = MODULES.filter(function(x){ return x.name === m.name && x.slug !== m.slug; });
  var dupeHtml = same.length ? '<div class="hint">另有 ' + same.length + ' 个同名模块，可在详情里对比：' + same.map(function(x){ return ' <span class="copy-link" data-dupe="' + esc(x.slug) + '">v' + esc(String(x.version || '').replace(/^v/, '')) + '</span>'; }).join('') + '</div>' : '';
  var surgeBtn = BASE_URL
    ? '<a class="btn import" href="' + esc(surgeInstallUrl(m)) + '">' + ICO_DOWN + '导入 Surge</a>'
    : '<span class="btn disabled" title="需部署到线上后可用">导入 Surge</span>';
  document.getElementById('modal').innerHTML =
    '<button class="btn close" id="modalClose">关闭 ✕</button>' +
    '<div class="card-top"><span class="cat">' + esc((m.category && m.category.name) || '') + '</span><span class="ver">' + esc(m.version || '') + '</span></div>' +
    '<h2>' + esc(m.name) + '</h2>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · ' + esc((m.category && m.category.name) || '') + ' · v' + esc(String(m.version || '').replace(/^v/, '')) + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + '</div>' +
    '<div class="desc-full">' + esc(m.description || '') + '</div>' +
    '<div class="tags" style="margin-top:10px">' + (m.tags || []).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
    dupeHtml +
    '<div class="kv"><div><span>作者：</span>' + esc(m.author || '') + '</div>' + repo + up +
    '<div><span>安装链接：</span><span id="instUrl">' + esc(url) + '</span></div></div>' +
    '<div class="linkrow"><div class="group">' + surgeBtn + '</div>' +
      '<div class="group"><button class="btn ghost" id="copyInst">' + ICO_LINK + '复制链接</button>' +
      '<button class="btn ghost" id="detailBtn">' + ICO_CFG + '详情配置</button></div>' +
    '</div>' +
    '<div class="hint">导入 Surge：在 Safari 中点上面的按钮，会直接打开 Surge 并提示安装。手动安装：点「复制链接」，再到 Surge → 模块 → 右上角 + → 粘贴链接（微信等 App 内打开时导入可能无效，请用手动方式）。<br>注意：部分模块需要开启 MITM 才能完整生效，证书钉扎的 App 请谨慎。</div>' +
    '<div class="tabs"><button class="btn" id="tabRaw">预览模块内容 ▸</button></div>' +
    '<div class="preview-summary" id="previewSummary" style="display:none"></div>' +
    '<pre class="raw" id="rawView" style="display:none">加载中…</pre>';
  document.getElementById('modalBg').classList.add('open');
  document.getElementById('modalClose').addEventListener('click', closeDetail);
  document.getElementById('copyInst').addEventListener('click', function(){ copyText(url, this); });
  document.getElementById('detailBtn').addEventListener('click', function(){
    var rv = document.getElementById('rawView');
    if (rv && rv.style.display === 'none') {
      rv.style.display = 'block';
      var tab = document.getElementById('tabRaw');
      if (tab) { tab.textContent = '收起模块内容 ▾'; tab.classList.add('on'); }
    }
    var el = document.getElementById('tabRaw');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.getElementById('tabRaw').addEventListener('click', function(){
    var rv = document.getElementById('rawView');
    var open = rv.style.display !== 'none';
    rv.style.display = open ? 'none' : 'block';
    this.textContent = open ? '预览模块内容 ▸' : '收起模块内容 ▾';
    this.classList.toggle('on', !open);
  });
  fetch(m.url).then(function(r){
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.text();
  }).then(function(t){
    var sum = parseModuleSummary(t);
    var sumEl = document.getElementById('previewSummary');
    sumEl.style.display = 'flex';
    sumEl.innerHTML = sum.html;
    document.getElementById('rawView').innerHTML = highlightModule(t);
  }).catch(function(err){
    var upLink = m.upstreamUrl ? ' <a href="' + esc(m.upstreamUrl) + '" target="_blank" rel="noopener">上游原文 ↗</a>' : '';
    document.getElementById('rawView').innerHTML = '无法直接读取本站的模块文件（' + esc(err.message) + '）。' +
      '如果是用 file:// 直接打开本页，浏览器会阻止读取本地文件；请用 http 服务（如 Cloudflare Pages）访问，或查看' + upLink + '。';
  });
}
function parseModuleSummary(text){
  var lines = text.split('\n');
  var sections = {};
  var cur = '';
  lines.forEach(function(ln){
    var mm = ln.match(/^\s*\[([^\]]+)\]\s*$/);
    if (mm) { cur = mm[1].trim(); sections[cur] = sections[cur] || []; return; }
    if (cur) sections[cur].push(ln);
  });
  function countReal(arr){
    return (arr || []).filter(function(ln){
      var t = ln.trim();
      return t !== '' && t.charAt(0) !== '#' && t.charAt(0) !== ';';
    }).length;
  }
  var hosts = [];
  (sections['MITM'] || []).forEach(function(ln){
    var mm = ln.match(/^\s*hostname\s*=\s*(.+)$/i);
    if (mm) mm[1].replace(/^\s*%APPEND%\s*/i, '').split(',').forEach(function(h){ h = h.trim(); if (h && h.charAt(0) !== '%') hosts.push(h); });
  });
  var hostHtml = hosts.length ? esc(hosts.slice(0, 5).join(', ')) + (hosts.length > 5 ? ' 等 ' + hosts.length + ' 个' : '') : '—';
  return { html:
    '<span>行数 <b>' + lines.length + '</b></span>' +
    '<span>规则 <b>' + countReal(sections['Rule']) + '</b> 条</span>' +
    '<span>脚本 <b>' + countReal(sections['Script']) + '</b> 个</span>' +
    '<span>MITM 域名 <b>' + hosts.length + '</b> 个</span>' +
    (hosts.length ? '<span style="word-break:break-all">' + hostHtml + '</span>' : '') };
}
function highlightModule(text){
  var lines = text.split('\n');
  var LIMIT = 5000;
  var html = lines.slice(0, LIMIT).map(function(ln){
    var e = esc(ln);
    if (/^\s*\[.*\]\s*$/.test(ln)) return '<span class="sec">' + e + '</span>';
    var t = ln.trim();
    if (t.charAt(0) === '#' || t.charAt(0) === ';') return '<span class="com">' + e + '</span>';
    return e;
  }).join('\n');
  if (lines.length > LIMIT) html += '\n<span class="com"># …文件较大，仅显示前 ' + LIMIT + ' 行（共 ' + lines.length + ' 行），完整内容请下载查看</span>';
  return html;
}
function closeDetail(){ document.getElementById('modalBg').classList.remove('open'); currentSlug = null; }
document.getElementById('modalBg').addEventListener('click', function(e){ if (e.target === this) closeDetail(); });
document.getElementById('modal').addEventListener('click', function(e){ var d = e.target.closest('[data-dupe]'); if (d) openDetail(d.getAttribute('data-dupe')); });
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeDetail(); });

var currentView = 'home';
var updShown = PAGE;
function refreshCurrentView(){
  if (currentView === 'fav') renderFav();
  else if (currentView === 'updates') renderUpdates();
  else if (currentView === 'home') renderHome();
  else render();
}
function dayLabel(iso){
  var p = String(iso || '').split('-');
  if (p.length !== 3) return iso || '';
  return p[0] + '年' + (+p[1]) + '月' + (+p[2]) + '日';
}
function updRowHtml(m, isLatest){
  return '<div class="upd-row" data-slug="' + esc(m.slug) + '">' +
    '<div class="upd-top"><span class="upd-name">' + esc(m.name) + '</span>' +
    '<span class="ver-badge">v' + esc(String(m.version || '').replace(/^v/, '')) + '</span>' +
    '<span class="tag">' + esc((m.category && m.category.name) || '') + '</span>' +
    (isLatest ? '<span class="latest-badge"><span class="latest-dot"></span>最新</span>' : '') +
    '<span class="upd-time">' + esc(relTime(m.updatedAt)) + '</span></div>' +
    (m.description ? '<div class="upd-desc">' + esc(m.description) + '</div>' : '') +
  '</div>';
}
function renderHome(){
  var byCat = {};
  MODULES.forEach(function(m){
    var c = (m.category && m.category.name) || '未分类';
    if (!byCat[c] || String(m.updatedAt || '') > String(byCat[c].updatedAt || '')) byCat[c] = m;
  });
  var catHtml = CATS.map(function(c){
    var top = byCat[c];
    var tags = top ? (top.tags || []).slice(0, 3).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') : '';
    return '<div class="catcard" data-catgo="' + esc(c) + '">' +
      '<div class="cat-eyebrow">' + esc(c) + ' <span>' + catCounts[c] + ' 个</span></div>' +
      (top ? '<h4>' + esc(top.name) + '<span class="ver">' + esc(top.version || '') + '</span></h4>' +
      '<p class="cat-desc">' + esc(top.description || '') + '</p>' +
      '<div class="tags">' + tags + '</div>' : '') +
      '<div class="go">查看全部 →</div></div>';
  }).join('');
  document.getElementById('catGrid').innerHTML = catHtml;
  document.getElementById('discCatGrid').innerHTML = catHtml;
  var newest = MODULES.slice().sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  document.getElementById('homeUpd').innerHTML = newest.slice(0, 5).map(updRowHtml).join('');
  document.getElementById('homeLib').innerHTML = newest.slice(0, 6).map(function(m){ return cardHtml(m); }).join('');
  var feat = CATS.map(function(c){ return byCat[c]; }).filter(Boolean)
    .sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); }).slice(0, 6);
  document.getElementById('featGrid').innerHTML = feat.map(function(m){ return cardHtml(m); }).join('');
}
function onCatCardClick(e){
  var t = e.target.closest('[data-catgo]'); if (!t) return;
  state.cat = t.getAttribute('data-catgo'); state.page = 1; renderPanel(); render(); showView('discover');
}
document.getElementById('catGrid').addEventListener('click', onCatCardClick);
document.getElementById('discCatGrid').addEventListener('click', onCatCardClick);
function renderFav(){
  var list = MODULES.filter(function(m){ return favs[m.slug]; });
  list.sort(function(a, b){
    var ta = favAdded[a.slug] || '', tb = favAdded[b.slug] || '';
    if (ta && tb) return tb.localeCompare(ta);
    if (ta) return -1;
    if (tb) return 1;
    return 0;
  });
  document.getElementById('favGrid').innerHTML = list.map(function(m){
    var t = favAdded[m.slug] ? '<p class="fav-time">收藏于 ' + esc(relTime(favAdded[m.slug])) + '</p>' : '';
    return '<div class="fav-item">' + cardHtml(m) + t + '</div>';
  }).join('');
  document.getElementById('favEmpty').style.display = list.length ? 'none' : 'block';
  var fc = document.getElementById('favCount');
  fc.style.display = list.length ? 'flex' : 'none';
  if (list.length) fc.innerHTML = '<span class="fav-num">' + list.length + '</span> 个收藏 · 按添加时间倒序';
}
function renderUpdates(){
  var list = MODULES.slice().sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  document.getElementById('updCount').textContent = list.length + ' 条';
  var shown = list.slice(0, updShown);
  var groups = [];
  shown.forEach(function(m){
    var key = fmtDate(m.updatedAt);
    var last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(m);
    else groups.push({ key: key, items: [m] });
  });
  document.getElementById('updGroups').innerHTML = groups.map(function(g, gi){
    var rows = g.items.map(function(m, mi){ return updRowHtml(m, gi === 0 && mi === 0); }).join('');
    return '<div class="upd-day"><div class="upd-day-head"><h3>' + esc(dayLabel(g.key)) + '</h3><span class="upd-day-line"></span><span class="upd-day-count">' + g.items.length + '</span></div><div class="upd-rows">' + rows + '</div></div>';
  }).join('');
  document.getElementById('updEmpty').style.display = list.length ? 'none' : 'block';
  document.getElementById('updMore').style.display = list.length > updShown ? 'block' : 'none';
}
document.getElementById('updReload').addEventListener('click', function(){ renderUpdates(); });
document.getElementById('updMore').addEventListener('click', function(){ updShown += PAGE; renderUpdates(); });
function showView(v){
  currentView = v;
  ['home','discover','fav','updates'].forEach(function(x){ document.getElementById('view-' + x).style.display = x === v ? 'block' : 'none'; });
  document.querySelectorAll('#bottomNav [data-nav]').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-nav') === v); });
  document.querySelectorAll('#topNav [data-nav]').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-nav') === v); });
  if (v === 'fav') renderFav();
  if (v === 'updates') renderUpdates();
  try { if (location.hash !== '#' + v) history.replaceState(null, '', '#' + v); } catch(e) {}
  window.scrollTo(0, 0);
}
document.getElementById('bottomNav').addEventListener('click', function(e){
  var b = e.target.closest('[data-nav]'); if (!b) return;
  showView(b.getAttribute('data-nav'));
});
var THEME_KEY = 'surge-index-theme';
var ICO_MOON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
var ICO_SUN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
function currentTheme(){ return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
function setTheme(m){
  document.documentElement.setAttribute('data-theme', m);
  document.documentElement.style.colorScheme = m;
  try { localStorage.setItem(THEME_KEY, m); } catch(e) {}
  var b = document.getElementById('themeBtn');
  if (b) { b.innerHTML = m === 'light' ? ICO_MOON : ICO_SUN; b.setAttribute('aria-label', m === 'light' ? '切换到深色' : '切换到浅色'); }
}
document.getElementById('themeBtn').addEventListener('click', function(){ setTheme(currentTheme() === 'light' ? 'dark' : 'light'); });
document.getElementById('topNav').addEventListener('click', function(e){
  var b = e.target.closest('[data-nav]'); if (!b) return;
  showView(b.getAttribute('data-nav'));
});
setTheme(currentTheme());

renderPanel();
render();
renderHome();
var initView = (location.hash || '#home').replace('#', '');
if (['home','discover','fav','updates'].indexOf(initView) === -1) initView = 'home';
showView(initView);
</script>
</body>
</html>
"""


def load_excluded():
    """Slugs excluded by the link-liveness audit (data-source/excluded.json).

    Removing a slug from excluded.json re-admits it on the next build/sync.
    """
    path = os.path.join(BASE, "data-source", "excluded.json")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {e["slug"] for e in json.load(f)}


def main():
    with open(SRC, encoding="utf-8") as f:
        entries = json.load(f)

    excluded = load_excluded()
    if excluded:
        entries = [e for e in entries if e.get("slug") not in excluded]

    entries.sort(key=lambda e: e.get("updatedAt") or "", reverse=True)
    max_updated = max((e.get("updatedAt") or "" for e in entries), default="")

    site_entries = []
    for e in entries:
        item = dict(e)
        item["upstreamUrl"] = e.get("rawUrl", "")
        item["url"] = f"/m/{e['slug']}.sgmodule"
        item["rawUrl"] = item["url"]
        site_entries.append(item)

    os.makedirs(os.path.dirname(OUT_DATA), exist_ok=True)
    with open(OUT_DATA, "w", encoding="utf-8") as f:
        json.dump(site_entries, f, ensure_ascii=False, separators=(",", ":"))

    authors = len({e.get("author") for e in site_entries if e.get("author")})
    cats = sorted({(e.get("category") or {}).get("name") for e in site_entries if (e.get("category") or {}).get("name")})
    cat_counts = {}
    for e in site_entries:
        c = (e.get("category") or {}).get("name")
        if c:
            cat_counts[c] = cat_counts.get(c, 0) + 1
    top_cat = max(cat_counts, key=lambda k: cat_counts[k]) if cat_counts else "—"

    def repo_root(u):
        if not u:
            return None
        p = urlparse(u)
        host = p.netloc.lower()
        parts = [x for x in p.path.split("/") if x]
        if host in ("github.com", "www.github.com") or "githubusercontent" in host:
            if len(parts) >= 2:
                return f"github.com/{parts[0]}/{parts[1]}"
        if host:
            return host + ("/" + parts[0] if parts else "")
        return None

    sources = len({repo_root(e.get("repositoryUrl") or "") for e in site_entries} - {None})
    last_dots = max_updated[:10].replace("-", ".") if max_updated else "—"

    data_json = json.dumps(site_entries, ensure_ascii=False, separators=(",", ":"))
    # Never allow the embedded JSON to break out of the <script> block.
    data_json = data_json.replace("</", "<\\/")

    # Snapshot stamp comes from the data itself (max updatedAt), never from
    # wall-clock time, so re-running with unchanged data is byte-identical.
    generated_at = (max_updated.replace("T", " ").replace("Z", "")[:16] + " UTC") if max_updated else "—"
    html = (TEMPLATE.replace("__MODULES_JSON__", data_json)
                    .replace("__TOTAL__", str(len(site_entries)))
                    .replace("__AUTHORS__", str(authors))
                    .replace("__CATS__", str(len(cats)))
                    .replace("__TOPCAT__", top_cat)
                    .replace("__SOURCES__", str(sources))
                    .replace("__LASTUPD_DOTS__", last_dots)
                    .replace("__UPDATED_AT__", max_updated[:10] or "—")
                    .replace("__GENERATED_AT__", generated_at))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"entries: {len(site_entries)}  max updatedAt: {max_updated}  authors: {authors}  cats: {len(cats)}  topcat: {top_cat}  sources: {sources}"
          + (f"  excluded: {len(excluded)}" if excluded else ""))
    print(f"wrote {OUT_DATA} ({os.path.getsize(OUT_DATA)} bytes)")
    print(f"wrote {OUT_HTML} ({os.path.getsize(OUT_HTML)} bytes)")


if __name__ == "__main__":
    main()
