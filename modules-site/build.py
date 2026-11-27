#!/usr/bin/env python3
"""Build the static Surge module index site.

Reads data-source/modules.json, rewrites each entry's rawUrl to the local
relative path /m/<slug>.sgmodule (original kept as upstreamUrl), writes
site/data/modules.json, and generates site/index.html — one self-contained
HTML file (inline CSS + JS, no external dependencies) with the module data
embedded, so it works from any static host and from file://.

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
<title>Surge 模块索引</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#f7f6f2;--card:#fff;--text:#1c1917;--muted:#78716c;--line:#e7e5e4;--accent:#047857;--accent-soft:#d1fae5;--tag:#f5f5f4;--ok:#15803d;--warn:#b45309}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);font-size:15px;line-height:1.5}
header{background:linear-gradient(135deg,#0d3b2e 0%,#14532d 60%,#166534 100%);color:#fff;padding:20px 16px 16px}
.brand{display:flex;align-items:center;gap:11px}
.logo{flex:0 0 auto;width:42px;height:42px;border-radius:12px;background:#fbbf24;color:#0d3b2e;font-size:23px;font-weight:700;display:flex;align-items:center;justify-content:center}
header h1{font-size:21px;letter-spacing:.5px;line-height:1.25}
header .tagline{font-size:12.5px;color:#a7f3d0;margin-top:2px}
header p{color:#d1fae5;font-size:13px;margin-top:10px;line-height:1.6}
header p b{color:#fff}
.toolbar{position:sticky;top:0;z-index:20;background:var(--bg);padding:10px 12px 8px;border-bottom:1px solid var(--line)}
.searchrow{display:flex;gap:8px}
#q{flex:1;padding:11px 12px;font-size:16px;border:1px solid var(--line);border-radius:10px;background:#fff;outline:none}
#q:focus{border-color:var(--accent)}
.btn{padding:0 14px;border:1px solid var(--line);border-radius:10px;background:#fff;font-size:14px;cursor:pointer;white-space:nowrap}
.btn.on{background:var(--accent);border-color:var(--accent);color:#fff}
.pills{display:flex;gap:6px;overflow-x:auto;padding:10px 0 2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.pills::-webkit-scrollbar{display:none}
.pill{flex:0 0 auto;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:#fff;font-size:13px;cursor:pointer;color:#333}
.pill.on{background:#14532d;border-color:#14532d;color:#fff}
.pill small{opacity:.65;margin-left:2px}
.subrow{display:flex;gap:8px;align-items:center;padding:8px 0 0}
.subrow select{padding:7px 8px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:14px}
#count{color:var(--muted);font-size:13px;margin-left:auto}
main{padding:12px;max-width:1060px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;cursor:pointer;position:relative}
.card:hover{border-color:var(--accent)}
.card h3{font-size:16px;padding-right:26px}
.card h3 .ver{font-size:12px;color:var(--muted);font-weight:400;margin-left:6px}
.meta{font-size:12.5px;color:var(--muted);margin-top:4px}
.desc{font-size:13.5px;color:#333;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:5px}
.tag{background:var(--tag);border-radius:6px;padding:2px 7px;font-size:12px;color:#555}
.badge{display:inline-block;border-radius:6px;padding:2px 7px;font-size:11.5px;margin-left:5px;vertical-align:1px}
.badge.panel{background:#e6f4ea;color:var(--ok)}
.badge.ok{background:#e6f4ea;color:var(--ok)}
.badge.unknown{background:#fef3c7;color:var(--warn)}
.star{position:absolute;top:10px;right:10px;border:none;background:none;font-size:19px;cursor:pointer;color:#c8c8c8;padding:2px 6px}
.star.fav{color:#f5a623}
.src-links{margin-top:9px;font-size:12.5px;display:flex;gap:14px}
.src-links a{color:var(--accent);text-decoration:none}
.src-links a:hover{text-decoration:underline}
.more{display:block;width:100%;margin:16px 0 8px;padding:12px;border:1px solid var(--line);border-radius:10px;background:#fff;font-size:15px;cursor:pointer}
.empty{color:var(--muted);text-align:center;padding:40px 0}
footer{color:var(--muted);font-size:12.5px;text-align:center;padding:18px 12px 28px;line-height:1.7}
.about{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;text-align:left;max-width:1060px;margin:0 auto 14px;color:#333}
.about b{font-size:14px}
.about a{color:var(--accent);text-decoration:none}
.about a:hover{text-decoration:underline}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;display:none;align-items:flex-end;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:#fff;width:100%;max-width:720px;max-height:88vh;overflow-y:auto;border-radius:16px 16px 0 0;padding:18px 16px calc(20px + env(safe-area-inset-bottom))}
.modal h2{font-size:19px;padding-right:60px}
.modal .meta{margin-top:6px}
.modal .desc-full{font-size:14.5px;margin-top:12px;white-space:pre-wrap;word-break:break-word}
.kv{margin-top:12px;font-size:13.5px}
.kv div{padding:5px 0;border-bottom:1px solid var(--line);word-break:break-all}
.kv span{color:var(--muted)}
.linkrow{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.linkrow .btn{padding:10px 14px}
.linkrow a.btn{text-decoration:none;color:var(--text);display:inline-block}
.hint{background:#f6f8fa;border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px;color:#444;margin-top:12px;line-height:1.7}
.tabs{display:flex;gap:8px;margin-top:16px}
.tabs .btn.on{background:#14532d;border-color:#14532d}
.btn.primary{background:#047857;border-color:#047857;color:#fff}
.linkrow a.btn.primary{color:#fff}
.btn.disabled{background:#e7e5e4;border-color:#e7e5e4;color:#a8a29e;cursor:not-allowed}
.preview-summary{display:flex;flex-wrap:wrap;gap:6px 14px;background:#f6f8fa;border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:12.5px;color:#444;margin-top:10px}
.preview-summary b{color:var(--text)}
.raw .sec{color:#047857;font-weight:700}
.raw .com{color:#78716c}
pre.raw{background:#0d1117;color:#e6edf3;border-radius:10px;padding:12px;font-size:12px;overflow:auto;max-height:50vh;white-space:pre;margin-top:10px}
.close{position:absolute;top:12px;right:12px}
@media(min-width:700px){.modal-bg{align-items:center;padding:20px}.modal{border-radius:16px}}
</style>
</head>
<body>
<header>
  <div class="brand"><span class="logo">模</span><div><h1>Surge 模块索引</h1><div class="tagline">公开模块目录 · 搜得到，装得上</div></div></div>
  <p>共 <b id="total">__TOTAL__</b> 个模块 · 数据更新至 <b>__UPDATED_AT__</b><br>
  独立镜像索引，与 Surge 官方无关；模块版权归原作者所有，作者信息均已保留。<br>
  数据来源：son.zhiaon.top（上游公开索引），本站仅作镜像收录。</p>
</header>
<div class="toolbar">
  <div class="searchrow">
    <input id="q" type="search" placeholder="搜索名称 / 作者 / 标签 / 拼音…" autocomplete="off">
    <button class="btn" id="favOnly">⭐ 只看收藏</button>
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
<main>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">没有找到匹配的模块，换个关键词试试。</div>
  <button class="more" id="more">加载更多</button>
</main>
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
var PAGE = 60;
var FAV_KEY = 'surge-modules-favs-v1';
var favs = {};
try { JSON.parse(localStorage.getItem(FAV_KEY) || '[]').forEach(function(s){ favs[s] = 1; }); } catch(e) {}
function saveFavs(){ try { localStorage.setItem(FAV_KEY, JSON.stringify(Object.keys(favs))); } catch(e) {} }
var state = { q:'', cat:'all', tag:'', favOnly:false, sort:'updated', shown:PAGE };
var BASE_URL = location.protocol.indexOf('http') === 0 ? location.origin : '';
function surgeInstallUrl(m){ return 'surge:///install-module?url=' + encodeURIComponent(BASE_URL + m.url); }

function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function fmtDate(s){ return s ? String(s).slice(0, 10) : ''; }

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
    if (state.favOnly && !favs[m.slug]) return false;
    if (state.cat !== 'all' && ((m.category && m.category.name) || '未分类') !== state.cat) return false;
    if (state.tag && (m.tags || []).indexOf(state.tag) === -1) return false;
    return matches(m, state.q);
  });
  if (state.sort === 'name') list.sort(function(a, b){ return String(a.name).localeCompare(String(b.name), 'zh'); });
  else list.sort(function(a, b){ return String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')); });
  return list;
}
function cardHtml(m){
  var health = m.health === 'ok' ? '<span class="badge ok">可用</span>' : '<span class="badge unknown">未检测</span>';
  var panel = m.hasPanel ? '<span class="badge panel">面板</span>' : '';
  var tags = (m.tags || []).slice(0, 4).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('');
  var links = '';
  if (BASE_URL) links += '<a href="' + surgeInstallUrl(m) + '">一键安装</a>';
  if (m.repositoryUrl) links += '<a href="' + esc(m.repositoryUrl) + '" target="_blank" rel="noopener">仓库 ↗</a>';
  if (m.upstreamUrl) links += '<a href="' + esc(m.upstreamUrl) + '" target="_blank" rel="noopener">上游原文 ↗</a>';
  return '<article class="card" data-slug="' + esc(m.slug) + '">' +
    '<button class="star' + (favs[m.slug] ? ' fav' : '') + '" data-star="' + esc(m.slug) + '" aria-label="收藏">' + (favs[m.slug] ? '★' : '☆') + '</button>' +
    '<h3>' + esc(m.name) + '<span class="ver">' + esc(m.version || '') + '</span>' + health + panel + '</h3>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · ' + esc((m.category && m.category.name) || '') + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + '</div>' +
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
document.getElementById('grid').addEventListener('click', function(e){
  if (e.target.closest('a')) return; // 卡片内的仓库 / 上游原文链接：直接跳转，不打开详情
  var star = e.target.closest('[data-star]');
  if (star) {
    e.stopPropagation();
    var slug = star.getAttribute('data-star');
    if (favs[slug]) delete favs[slug]; else favs[slug] = 1;
    saveFavs(); render(); return;
  }
  var card = e.target.closest('[data-slug]');
  if (card) openDetail(card.getAttribute('data-slug'));
});
document.getElementById('more').addEventListener('click', function(){ state.shown += PAGE; render(); });
var qTimer = null;
document.getElementById('q').addEventListener('input', function(e){
  clearTimeout(qTimer);
  qTimer = setTimeout(function(){ state.q = e.target.value.trim(); state.shown = PAGE; render(); }, 150);
});
document.getElementById('favOnly').addEventListener('click', function(){
  state.favOnly = !state.favOnly;
  this.classList.toggle('on', state.favOnly); state.shown = PAGE; render();
});
document.getElementById('sort').addEventListener('change', function(e){ state.sort = e.target.value; render(); });

function installUrl(m){
  if (location.protocol.indexOf('http') === 0) return location.origin + m.url;
  return m.url;
}
function copyText(t, btn){
  function done(){ if (btn) { var o = btn.textContent; btn.textContent = '已复制 ✓'; setTimeout(function(){ btn.textContent = o; }, 1500); } }
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
    ? '<a class="btn primary" href="' + esc(surgeInstallUrl(m)) + '">一键添加到 Surge</a>'
    : '<span class="btn disabled" title="需部署到线上后可用">一键添加到 Surge</span>';
  document.getElementById('modal').innerHTML =
    '<button class="btn close" id="modalClose">关闭 ✕</button>' +
    '<h2>' + esc(m.name) + '</h2>' +
    '<div class="meta">作者：' + esc(m.author || '') + ' · ' + esc((m.category && m.category.name) || '') + ' · v' + esc(String(m.version || '').replace(/^v/, '')) + ' · 更新 ' + esc(fmtDate(m.updatedAt)) + '</div>' +
    '<div class="desc-full">' + esc(m.description || '') + '</div>' +
    '<div class="tags" style="margin-top:10px">' + (m.tags || []).map(function(t){ return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>' +
    '<div class="kv"><div><span>作者：</span>' + esc(m.author || '') + '</div>' + repo + up +
    '<div><span>安装链接：</span><span id="instUrl">' + esc(url) + '</span></div></div>' +
    '<div class="linkrow">' + surgeBtn +
      '<button class="btn" id="copyInst">复制安装链接</button>' +
      '<button class="btn" id="favBtn">' + (favs[m.slug] ? '★ 已收藏' : '☆ 收藏') + '</button>' +
    '</div>' +
    '<div class="hint">一键安装：在 Safari 中点上面的按钮，会直接打开 Surge 并提示安装。手动安装：点「复制安装链接」，再到 Surge → 模块 → 右上角 + → 粘贴链接（微信等 App 内打开时一键安装可能无效，请用手动方式）。<br>注意：部分模块需要开启 MITM 才能完整生效，证书钉扎的 App 请谨慎。</div>' +
    '<div class="tabs"><button class="btn on" id="tabRaw">预览模块内容</button></div>' +
    '<div class="preview-summary" id="previewSummary" style="display:none"></div>' +
    '<pre class="raw" id="rawView">加载中…</pre>';
  document.getElementById('modalBg').classList.add('open');
  document.getElementById('modalClose').addEventListener('click', closeDetail);
  document.getElementById('copyInst').addEventListener('click', function(){ copyText(url, this); });
  document.getElementById('favBtn').addEventListener('click', function(){
    if (favs[m.slug]) delete favs[m.slug]; else favs[m.slug] = 1;
    saveFavs(); this.textContent = favs[m.slug] ? '★ 已收藏' : '☆ 收藏'; render();
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

renderFilters();
render();
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

    data_json = json.dumps(site_entries, ensure_ascii=False, separators=(",", ":"))
    # Never allow the embedded JSON to break out of the <script> block.
    data_json = data_json.replace("</", "<\\/")

    # Snapshot stamp comes from the data itself (max updatedAt), never from
    # wall-clock time, so re-running with unchanged data is byte-identical.
    generated_at = (max_updated.replace("T", " ").replace("Z", "")[:16] + " UTC") if max_updated else "—"
    html = (TEMPLATE.replace("__MODULES_JSON__", data_json)
                    .replace("__TOTAL__", str(len(site_entries)))
                    .replace("__UPDATED_AT__", max_updated[:10] or "—")
                    .replace("__GENERATED_AT__", generated_at))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"entries: {len(site_entries)}  max updatedAt: {max_updated}"
          + (f"  excluded: {len(excluded)}" if excluded else ""))
    print(f"wrote {OUT_DATA} ({os.path.getsize(OUT_DATA)} bytes)")
    print(f"wrote {OUT_HTML} ({os.path.getsize(OUT_HTML)} bytes)")


if __name__ == "__main__":
    main()
