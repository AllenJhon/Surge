#!/usr/bin/env python3
"""Build the static Surge module index site.

Reads data-source/modules.json, rewrites each entry's rawUrl to the local
relative path /m/<slug>.sgmodule (original kept as upstreamUrl), writes
site/data/modules.json, and generates site/index.html — one HTML file with
inline CSS + JS and the module data embedded, so it works from any static
host and from file://. The header logo is the Surge app icon, embedded as a
base64 data URI (source: fmz200 icon collection, re-fetchable from
https://raw.githubusercontent.com/fmz200/wool_scripts/main/icons/apps/Surge.png),
so the page stays a single file.

Usage: python3 build.py
Safe to re-run; output is fully deterministic — the snapshot stamp comes
from the data's max updatedAt, never wall-clock time, so an unchanged
upstream produces byte-identical output (no empty sync commits).
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "data-source", "modules.json")
OUT_DATA = os.path.join(BASE, "site", "data", "modules.json")
OUT_HTML = os.path.join(BASE, "site", "index.html")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Surge</title>
<link rel="icon" type="image/png" href="data:image/png;base64,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">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0b0d12;--card:#15181f;--text:#e6e8eb;--muted:#9aa3af;--line:#262b36;--accent:#10b981;--accent-soft:#064e3b;--tag:#171b23;--ok:#34d399;--warn:#fbbf24}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);font-size:15px;line-height:1.5}
header{background:#11141b;color:#e6e8eb;padding:20px 16px 16px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:11px}
img.logo{flex:0 0 auto;width:42px;height:42px;border-radius:11px;background:#fff;object-fit:cover}
header h1{font-size:21px;letter-spacing:.5px;line-height:1.25}
header .tagline{font-size:12.5px;color:#9aa3af;margin-top:2px}
header p{color:#9aa3af;font-size:13px;margin-top:10px;line-height:1.6}
header p b{color:#fff}
.toolbar{position:sticky;top:0;z-index:20;background:var(--bg);padding:10px 12px 8px;border-bottom:1px solid var(--line)}
.searchrow{display:flex;gap:8px}
#q{flex:1;padding:11px 12px;font-size:16px;border:1px solid var(--line);border-radius:10px;background:#171b23;color:var(--text);outline:none}
#q:focus{border-color:var(--accent)}
.btn{padding:0 14px;border:1px solid var(--line);border-radius:10px;background:#171b23;color:var(--text);font-size:14px;cursor:pointer;white-space:nowrap}
.btn.on{background:var(--accent);border-color:var(--accent);color:#06281c}
.pills{display:flex;gap:6px;overflow-x:auto;padding:10px 0 2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.pills::-webkit-scrollbar{display:none}
.pill{flex:0 0 auto;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:#171b23;font-size:13px;cursor:pointer;color:#c6cbd4}
.pill.on{background:var(--accent);border-color:var(--accent);color:#06281c}
.pill small{opacity:.65;margin-left:2px}
.subrow{display:flex;gap:8px;align-items:center;padding:8px 0 0}
.subrow select{padding:7px 8px;border:1px solid var(--line);border-radius:8px;background:#171b23;color:var(--text);font-size:14px}
#count{color:var(--muted);font-size:13px;margin-left:auto}
main{padding:12px;max-width:1060px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;cursor:pointer;position:relative}
.card:hover{border-color:var(--accent)}
.card h3{font-size:16px;padding-right:26px}
.card h3 .ver{font-size:12px;color:var(--muted);font-weight:400;margin-left:6px}
.meta{font-size:12.5px;color:var(--muted);margin-top:4px}
.desc{font-size:13.5px;color:#c6cbd4;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:5px}
.tag{background:var(--tag);border-radius:6px;padding:2px 7px;font-size:12px;color:#9aa3af}
.badge{display:inline-block;border-radius:6px;padding:2px 7px;font-size:11.5px;margin-left:5px;vertical-align:1px}
.badge.panel{background:#064e3b;color:var(--ok)}
.badge.ok{background:#064e3b;color:var(--ok)}
.badge.unknown{background:#422006;color:var(--warn)}
.detail-link{font-size:11.5px;color:var(--accent);cursor:pointer;margin-left:6px;vertical-align:1px;font-weight:400;white-space:nowrap}
.detail-link:hover{text-decoration:underline}
.copy-link{color:var(--accent);cursor:pointer}
.copy-link:hover{text-decoration:underline}
.linkrow{justify-content:space-between;align-items:center}
.linkrow .group{display:flex;gap:8px;flex-wrap:wrap}
.btn.import{background:#fff;border-color:#fff;color:#111827;border-radius:999px;padding:10px 18px;font-weight:600;display:inline-flex;align-items:center;gap:6px}
.linkrow a.btn.import{color:#111827}
.btn.ghost{background:transparent;border:1px solid #2e3440;color:#e6e8eb;border-radius:999px;padding:10px 16px;display:inline-flex;align-items:center;gap:6px}
.btn.ghost:hover{border-color:#4b5563}
.star{position:absolute;top:10px;right:10px;border:none;background:none;font-size:19px;cursor:pointer;color:#4b5563;padding:2px 6px}
.star.fav{color:#f5a623}
.src-links{margin-top:9px;font-size:12.5px;display:flex;gap:14px}
.src-links a{color:var(--accent);text-decoration:none}
.src-links a:hover{text-decoration:underline}
.more{display:block;width:100%;margin:16px 0 8px;padding:12px;border:1px solid var(--line);border-radius:10px;background:#171b23;color:var(--text);font-size:15px;cursor:pointer}
.empty{color:var(--muted);text-align:center;padding:40px 0}
footer{color:var(--muted);font-size:12.5px;text-align:center;padding:18px 12px 28px;line-height:1.7}
.about{background:#15181f;border:1px solid var(--line);border-radius:12px;padding:14px 16px;text-align:left;max-width:1060px;margin:0 auto 14px;color:#c6cbd4}
.about b{font-size:14px}
.about a{color:var(--accent);text-decoration:none}
.about a:hover{text-decoration:underline}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:none;align-items:flex-end;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:#15181f;width:100%;max-width:720px;max-height:88vh;overflow-y:auto;border-radius:16px 16px 0 0;padding:18px 16px calc(20px + env(safe-area-inset-bottom))}
.modal h2{font-size:19px;padding-right:60px}
.modal .meta{margin-top:6px}
.modal .desc-full{font-size:14.5px;margin-top:12px;white-space:pre-wrap;word-break:break-word}
.kv{margin-top:12px;font-size:13.5px}
.kv div{padding:5px 0;border-bottom:1px solid var(--line);word-break:break-all}
.kv span{color:var(--muted)}
.linkrow{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.linkrow .btn{padding:10px 14px}
.linkrow a.btn{text-decoration:none;color:var(--text);display:inline-block}
.hint{background:#171b23;border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px;color:#c6cbd4;margin-top:12px;line-height:1.7}
.tabs{display:flex;gap:8px;margin-top:16px}
.tabs .btn.on{background:var(--accent);border-color:var(--accent);color:#06281c}
.btn.primary{background:#10b981;border-color:#10b981;color:#06281c}
.linkrow a.btn.primary{color:#06281c}
.btn.disabled{background:#262b36;border-color:#262b36;color:#6b7280;cursor:not-allowed}
.preview-summary{display:flex;flex-wrap:wrap;gap:6px 14px;background:#171b23;border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:12.5px;color:#c6cbd4;margin-top:10px}
.preview-summary b{color:var(--text)}
.raw .sec{color:#34d399;font-weight:700}
.raw .com{color:#6b7280}
pre.raw{background:#0d1117;color:#e6edf3;border-radius:10px;padding:12px;font-size:12px;overflow:auto;max-height:50vh;white-space:pre;margin-top:10px}
.close{position:absolute;top:12px;right:12px}
body{padding-bottom:92px}
.hero{padding:26px 6px 8px;text-align:center}
.hero h2{font-size:30px;letter-spacing:.5px}
.hero-sub{color:var(--muted);font-size:14px;margin-top:6px}
.hero-search{display:flex;gap:8px;max-width:560px;margin:16px auto 0}
#hq{flex:1;padding:12px 14px;font-size:16px;border:1px solid var(--line);border-radius:12px;background:#171b23;color:var(--text);outline:none}
#hq:focus{border-color:var(--accent)}
.hero-stats{margin-top:14px;font-size:13.5px;color:var(--muted)}
.hero-stats b{color:var(--text)}
.hero-note{max-width:640px;margin:10px auto 0;font-size:12.5px;color:var(--muted);line-height:1.7}
.sec-title{font-size:19px;margin:26px 0 2px}
.sec-sub{color:var(--muted);font-size:13px;margin-bottom:12px}
.catgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
.catcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;cursor:pointer}
.catcard:hover{border-color:var(--accent)}
.catcard h4{font-size:16px}
.catcard h4 small{color:var(--muted);font-weight:400;margin-left:6px}
.catcard p{font-size:13px;color:#c6cbd4;margin-top:6px}
.catcard .go{font-size:12.5px;color:var(--accent);margin-top:8px}
.about-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.about-card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.about-card b{font-size:15px}
.about-card p{font-size:13px;color:#c6cbd4;margin-top:6px;line-height:1.7}
.nav{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(14px + env(safe-area-inset-bottom));z-index:40;display:flex;width:min(480px,calc(100% - 24px));background:rgba(21,24,31,.97);border:1px solid var(--line);border-radius:999px;padding:6px 8px;box-shadow:0 8px 28px rgba(0,0,0,.45)}
.nav button{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;background:none;border:none;color:#9aa3af;font-size:12px;padding:6px 0 5px;cursor:pointer;position:relative}
.nav button svg{display:block}
.nav button.on{color:var(--accent)}
.nav button.on::after{content:'';position:absolute;left:50%;transform:translateX(-50%);bottom:-1px;width:22px;height:3px;border-radius:2px;background:var(--accent)}
@media(min-width:700px){.modal-bg{align-items:center;padding:20px}.modal{border-radius:16px}}
</style>
</head>
<body>
<header>
  <div class="brand"><img class="logo" src="data:image/png;base64,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" alt="Surge"><div><h1>Surge</h1><div class="tagline">公开模块目录 · 搜得到，装得上</div></div></div>
</header>
<main>
  <section id="view-home">
    <div class="hero">
      <h2>Surge 模块索引</h2>
      <p class="hero-sub">公开模块目录 · 搜得到，装得上</p>
      <div class="hero-search">
        <input id="hq" type="search" placeholder="搜模块、作者、标签…" autocomplete="off">
        <button class="btn" id="hqBtn" style="padding:0 18px">搜索</button>
      </div>
      <div class="hero-stats">共 <b>__TOTAL__</b> 个模块 · <b>__AUTHORS__</b> 位作者 · <b>__CATS__</b> 个分类 · 数据更新至 <b>__UPDATED_AT__</b></div>
      <p class="hero-note">独立镜像索引，与 Surge 官方无关；模块版权归原作者所有，作者信息均已保留。数据来源：son.zhiaon.top（上游公开索引），本站仅作镜像收录，每天自动同步。</p>
    </div>
    <h2 class="sec-title">本周精选</h2>
    <p class="sec-sub">最近更新、介绍完整的模块，先从这里看起。</p>
    <div class="grid" id="featGrid"></div>
    <h2 class="sec-title">按分类浏览</h2>
    <p class="sec-sub">按用途找：从去广告到脚本增强。</p>
    <div class="catgrid" id="catGrid"></div>
    <h2 class="sec-title">关于本站</h2>
    <p class="sec-sub">一个只做索引的站，没有社区，没有商店。</p>
    <div class="about-grid">
      <div class="about-card"><b>独立索引</b><p>数据来自上游公开索引，本站独立维护，与 Surge 官方无关。</p></div>
      <div class="about-card"><b>一键导入</b><p>复制安装链接，或直接把模块交给 Surge 安装。</p></div>
      <div class="about-card"><b>内容预览</b><p>先看模块原文：规则、脚本、MITM 域名一目了然。</p></div>
      <div class="about-card"><b>本地收藏</b><p>收藏只存在这个浏览器里，不用注册，清空站点数据就没了。</p></div>
    </div>
  </section>
  <section id="view-discover" style="display:none">
    <div class="toolbar">
      <div class="searchrow">
        <input id="q" type="search" placeholder="搜索名称 / 作者 / 标签 / 拼音…" autocomplete="off">
      </div>
      <div class="pills" id="cats"></div>
      <div class="pills" id="tags"></div>
      <div class="subrow">
        <select id="sort">
          <option value="updated">按更新时间</option>
          <option value="name">按名称</option>
        </select>
        <span id="count"></span>
      </div>
    </div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" style="display:none">没有找到匹配的模块，换个关键词试试。</div>
    <button class="more" id="more">加载更多</button>
  </section>
  <section id="view-fav" style="display:none">
    <div class="grid" id="favGrid"></div>
    <div class="empty" id="favEmpty">还没有收藏。点卡片右上角的 ☆，把喜欢的模块收进来。</div>
  </section>
  <section id="view-updates" style="display:none">
    <div class="grid" id="updGrid"></div>
    <button class="more" id="updMore">加载更多</button>
  </section>
</main>
<nav class="nav" id="bottomNav">
  <button data-nav="home" class="on"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>首页</button>
  <button data-nav="discover"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>发现</button>
  <button data-nav="fav"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>收藏</button>
  <button data-nav="updates"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>更新</button>
</nav>
<footer>
  <div class="about">
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
var FEATURED = __FEATURED_JSON__;
var PAGE = 60;
var FAV_KEY = 'surge-modules-favs-v1';
var favs = {};
try { JSON.parse(localStorage.getItem(FAV_KEY) || '[]').forEach(function(s){ favs[s] = 1; }); } catch(e) {}
function saveFavs(){ try { localStorage.setItem(FAV_KEY, JSON.stringify(Object.keys(favs))); } catch(e) {} }
var state = { q:'', cat:'all', tag:'', sort:'updated', shown:PAGE };
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

function pillHtml(list, counts, active, key){
  var h = '<span class="pill' + (active === 'all' ? ' on' : '') + '" data-' + key + '="all">全部</span>';
  list.forEach(function(name){
    h += '<span class="pill' + (active === name ? ' on' : '') + '" data-' + key + '="' + esc(name) + '">' + esc(name) + '<small>' + counts[name] + '</small></span>';
  });
  return h;
}
function renderFilters(){
  document.getElementById('cats').innerHTML = pillHtml(CATS, catCounts, state.cat, 'cat');
  document.getElementById('tags').innerHTML = pillHtml(TOP_TAGS, tagCounts, state.tag || 'all', 'tag');
}
document.getElementById('cats').addEventListener('click', function(e){
  var t = e.target.closest('[data-cat]'); if (!t) return;
  state.cat = t.getAttribute('data-cat'); state.shown = PAGE; renderFilters(); render();
});
document.getElementById('tags').addEventListener('click', function(e){
  var t = e.target.closest('[data-tag]'); if (!t) return;
  var v = t.getAttribute('data-tag');
  state.tag = (v === 'all' || state.tag === v) ? '' : v; state.shown = PAGE; renderFilters(); render();
});

function matches(m, q){
  if (!q) return true;
  var hay = [m.name, m.author, (m.tags || []).join(' '), m.description,
             (m.py && m.py.full) || '', (m.py && m.py.initials) || ''].join(' ').toLowerCase();
  return q.toLowerCase().split(/\s+/).every(function(t){ return t && hay.indexOf(t) !== -1; });
}
function filtered(){
  var list = MODULES.filter(function(m){
    if (state.cat !== 'all' && ((m.category && m.category.name) || '未分类') !== state.cat) return false;
    if (state.tag && (m.tags || []).indexOf(state.tag) === -1) return false;
    return matches(m, state.q);
  });
  if (state.sort === 'name') list.sort(function(a, b){ return String(a.name).localeCompare(String(b.name), 'zh'); });
  else list.sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  return list;
}
function cardHtml(m, rel){
  var health = m.health === 'ok' ? '<span class="badge ok">可用</span>' : '<span class="badge unknown">未检测</span>';
  var panel = m.hasPanel ? '<span class="badge panel">面板</span>' : '';
  var tags = (m.tags || []).slice(0, 4).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('');
  var links = '';
  if (BASE_URL) links += '<span class="copy-link" data-copy="' + esc(installUrl(m)) + '">复制链接</span>';
  if (BASE_URL) links += '<a href="' + surgeInstallUrl(m) + '">导入 Surge</a>';
  if (m.repositoryUrl) links += '<a href="' + esc(m.repositoryUrl) + '" target="_blank" rel="noopener">仓库 ↗</a>';
  if (m.upstreamUrl) links += '<a href="' + esc(m.upstreamUrl) + '" target="_blank" rel="noopener">上游原文 ↗</a>';
  return '<article class="card" data-slug="' + esc(m.slug) + '">' +
    '<button class="star' + (favs[m.slug] ? ' fav' : '') + '" data-star="' + esc(m.slug) + '" aria-label="收藏">' + (favs[m.slug] ? '★' : '☆') + '</button>' +
    '<h3>' + esc(m.name) + '<span class="ver">' + esc(m.version || '') + '</span>' + health + panel + '<span class="detail-link">详情配置</span></h3>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · ' + esc((m.category && m.category.name) || '') + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + (rel ? ' · ' + esc(rel) : '') + '</div>' +
    '<div class="desc">' + esc(m.description || '') + '</div>' +
    '<div class="tags">' + tags + '</div>' +
    '<div class="src-links">' + links + '</div></article>';
}
function render(){
  var list = filtered();
  document.getElementById('count').textContent = '共 ' + list.length + ' 个，显示 ' + Math.min(state.shown, list.length) + ' 个';
  document.getElementById('empty').style.display = list.length ? 'none' : 'block';
  document.getElementById('grid').innerHTML = list.slice(0, state.shown).map(cardHtml).join('');
  document.getElementById('more').style.display = list.length > state.shown ? 'block' : 'none';
}
function onGridClick(e){
  if (e.target.closest('a')) return; // 卡片内的仓库 / 上游原文链接：直接跳转，不打开详情
  var cp = e.target.closest('[data-copy]');
  if (cp) { copyText(cp.getAttribute('data-copy'), cp); return; }
  var star = e.target.closest('[data-star]');
  if (star) {
    e.stopPropagation();
    var slug = star.getAttribute('data-star');
    if (favs[slug]) delete favs[slug]; else favs[slug] = 1;
    saveFavs(); refreshCurrentView(); return;
  }
  var card = e.target.closest('[data-slug]');
  if (card) openDetail(card.getAttribute('data-slug'));
}
['grid','featGrid','favGrid','updGrid'].forEach(function(id){ document.getElementById(id).addEventListener('click', onGridClick); });
document.getElementById('more').addEventListener('click', function(){ state.shown += PAGE; render(); });
var qTimer = null;
document.getElementById('q').addEventListener('input', function(e){
  clearTimeout(qTimer);
  qTimer = setTimeout(function(){ state.q = e.target.value.trim(); state.shown = PAGE; render(); }, 150);
});
document.getElementById('sort').addEventListener('change', function(e){ state.sort = e.target.value; render(); });

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
  var surgeBtn = BASE_URL
    ? '<a class="btn import" href="' + esc(surgeInstallUrl(m)) + '">' + ICO_DOWN + '导入 Surge</a>'
    : '<span class="btn disabled" title="需部署到线上后可用">导入 Surge</span>';
  document.getElementById('modal').innerHTML =
    '<button class="btn close" id="modalClose">关闭 ✕</button>' +
    '<h2>' + esc(m.name) + '</h2>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · ' + esc((m.category && m.category.name) || '') + ' · v' + esc(String(m.version || '').replace(/^v/, '')) + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + '</div>' +
    '<div class="desc-full">' + esc(m.description || '') + '</div>' +
    '<div class="tags" style="margin-top:10px">' + (m.tags || []).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
    '<div class="kv"><div><span>作者：</span>' + esc(m.author || '') + '</div>' + repo + up +
    '<div><span>安装链接：</span><span id="instUrl">' + esc(url) + '</span></div></div>' +
    '<div class="linkrow"><div class="group">' + surgeBtn + '</div>' +
      '<div class="group"><button class="btn ghost" id="copyInst">' + ICO_LINK + '复制链接</button>' +
      '<button class="btn ghost" id="detailBtn">' + ICO_CFG + '详情配置</button></div>' +
    '</div>' +
    '<div class="hint">导入 Surge：在 Safari 中点上面的按钮，会直接打开 Surge 并提示安装。手动安装：点「复制链接」，再到 Surge → 模块 → 右上角 + → 粘贴链接（微信等 App 内打开时导入可能无效，请用手动方式）。<br>注意：部分模块需要开启 MITM 才能完整生效，证书钉扎的 App 请谨慎。</div>' +
    '<div class="tabs"><button class="btn on" id="tabRaw">预览模块内容</button></div>' +
    '<div class="preview-summary" id="previewSummary" style="display:none"></div>' +
    '<pre class="raw" id="rawView">加载中…</pre>';
  document.getElementById('modalBg').classList.add('open');
  document.getElementById('modalClose').addEventListener('click', closeDetail);
  document.getElementById('copyInst').addEventListener('click', function(){ copyText(url, this); });
  document.getElementById('detailBtn').addEventListener('click', function(){
    var el = document.getElementById('tabRaw');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeDetail(); });

var currentView = 'home';
var updShown = PAGE;
function refreshCurrentView(){
  if (currentView === 'fav') renderFav();
  else if (currentView === 'updates') renderUpdates();
  else if (currentView === 'home') renderHome();
  else render();
}
function renderHome(){
  var feat = FEATURED.map(function(slug){ var m = null; MODULES.forEach(function(x){ if (x.slug === slug) m = x; }); return m; }).filter(Boolean);
  document.getElementById('featGrid').innerHTML = feat.map(function(m){ return cardHtml(m); }).join('');
  var byCat = {};
  MODULES.forEach(function(m){
    var c = (m.category && m.category.name) || '未分类';
    if (!byCat[c] || String(m.updatedAt || '') > String(byCat[c].updatedAt || '')) byCat[c] = m;
  });
  document.getElementById('catGrid').innerHTML = CATS.map(function(c){
    var top = byCat[c];
    return '<div class="catcard" data-catgo="' + esc(c) + '"><h4>' + esc(c) + '<small>' + catCounts[c] + ' 个</small></h4>' +
      (top ? '<p>最新：' + esc(top.name) + ' v' + esc(String(top.version || '').replace(/^v/, '')) + '</p>' : '') +
      '<div class="go">查看全部 →</div></div>';
  }).join('');
}
document.getElementById('catGrid').addEventListener('click', function(e){
  var t = e.target.closest('[data-catgo]'); if (!t) return;
  state.cat = t.getAttribute('data-catgo'); state.shown = PAGE; renderFilters(); render(); showView('discover');
});
function renderFav(){
  var list = MODULES.filter(function(m){ return favs[m.slug]; });
  document.getElementById('favGrid').innerHTML = list.map(function(m){ return cardHtml(m); }).join('');
  document.getElementById('favEmpty').style.display = list.length ? 'none' : 'block';
}
function renderUpdates(){
  var list = MODULES.slice().sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  document.getElementById('updGrid').innerHTML = list.slice(0, updShown).map(function(m){ return cardHtml(m, relTime(m.updatedAt)); }).join('');
  document.getElementById('updMore').style.display = list.length > updShown ? 'block' : 'none';
}
document.getElementById('updMore').addEventListener('click', function(){ updShown += PAGE; renderUpdates(); });
function showView(v){
  currentView = v;
  ['home','discover','fav','updates'].forEach(function(x){ document.getElementById('view-' + x).style.display = x === v ? 'block' : 'none'; });
  document.querySelectorAll('#bottomNav [data-nav]').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-nav') === v); });
  if (v === 'fav') renderFav();
  if (v === 'updates') renderUpdates();
  try { if (location.hash !== '#' + v) history.replaceState(null, '', '#' + v); } catch(e) {}
  window.scrollTo(0, 0);
}
document.getElementById('bottomNav').addEventListener('click', function(e){
  var b = e.target.closest('[data-nav]'); if (!b) return;
  showView(b.getAttribute('data-nav'));
});
function homeSearch(){
  state.q = document.getElementById('hq').value.trim();
  document.getElementById('q').value = state.q;
  state.shown = PAGE; render(); showView('discover');
}
document.getElementById('hqBtn').addEventListener('click', homeSearch);
document.getElementById('hq').addEventListener('keydown', function(e){ if (e.key === 'Enter') homeSearch(); });

renderFilters();
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
    feat_cats = ["广告拦截", "应用解锁", "脚本增强", "流媒体", "网络工具", "Apple 服务"]
    featured = []
    for c in feat_cats:
        ms = [e for e in site_entries if (e.get("category") or {}).get("name") == c and len(e.get("description") or "") >= 60]
        if not ms:
            continue
        ms.sort(key=lambda e: ((1 if e.get("hasPanel") else 0), e.get("updatedAt") or ""), reverse=True)
        featured.append(ms[0]["slug"])

    data_json = json.dumps(site_entries, ensure_ascii=False, separators=(",", ":"))
    # Never allow the embedded JSON to break out of the <script> block.
    data_json = data_json.replace("</", "<\\/")

    # Snapshot stamp comes from the data itself (max updatedAt), never from
    # wall-clock time, so re-running with unchanged data is byte-identical.
    generated_at = (max_updated.replace("T", " ").replace("Z", "")[:16] + " UTC") if max_updated else "—"
    html = (TEMPLATE.replace("__MODULES_JSON__", data_json)
                    .replace("__FEATURED_JSON__", json.dumps(featured, ensure_ascii=False))
                    .replace("__TOTAL__", str(len(site_entries)))
                    .replace("__AUTHORS__", str(authors))
                    .replace("__CATS__", str(len(cats)))
                    .replace("__UPDATED_AT__", max_updated[:10] or "—")
                    .replace("__GENERATED_AT__", generated_at))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"entries: {len(site_entries)}  max updatedAt: {max_updated}  authors: {authors}  cats: {len(cats)}  featured: {featured}"
          + (f"  excluded: {len(excluded)}" if excluded else ""))
    print(f"wrote {OUT_DATA} ({os.path.getsize(OUT_DATA)} bytes)")
    print(f"wrote {OUT_HTML} ({os.path.getsize(OUT_HTML)} bytes)")


if __name__ == "__main__":
    main()
