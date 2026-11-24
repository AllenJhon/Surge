// 酷狗概念版每日自动领取 VIP（Surge 模块）
// ============================================================
// 用途：每天自动完成「天天签到领VIP」：听歌任务 1 次 + 领 VIP 最多 8 次，
//       成功后用 $notification 汇报结果。
// 原理：复刻 MakcRe/KuGouMusicApi 的 android 签名（MD5），
//       直接调用酷狗概念版 App 自身的两个接口。
// 依赖：纯 JS，不依赖任何 Node 内置模块（MD5 已内联）。
//
// 使用步骤：
//  1. 安装本模块（.sgmodule），并在 Surge 里开启 MITM，信任证书。
//  2. 打开酷狗概念版 App，进入「活动中心 → 天天签到领VIP」，
//     点一次「领取」（当天已领过也没关系，抓 token 用）。
//     抓包脚本会把 token / dfid / userid / appid 等存下来，并弹通知确认。
//     看到「Token 已抓取」通知后，在 Surge「模块」里关闭「酷狗概念版抓包」
//     这一项（避免每次打开 App 都触发抓包），只保留两个定时任务。
//  3. 每天 08:00 执行听歌 + 前 4 次领 VIP；08:10 补领后 4 次。
//     每次执行完都会弹通知汇报结果。
// 注意：
//  - token 有效期约两个月，过期后领取会失败；重新按步骤 2 点一次领取即可。
//  - 若酷狗 App 启用了证书锁定（SSL Pinning），MITM 抓包会失败，
//    那就抓不到 token，本模块无法使用（这是唯一无法绕过的 blocker）。
//  - 本脚本不做登录、不做扫码、不刷新 token，只用抓到的 token 调接口。
// ============================================================

// ---------------- MD5（纯 JS 实现，RFC 1321，已验证） ----------------
function md5(input) {
  function rhex(n) {
    var s = '', j;
    for (j = 0; j < 4; j++) s += ('0' + ((n >> (j * 8 + 4)) & 0x0F).toString(16)).slice(-1) + ('0' + ((n >> (j * 8)) & 0x0F).toString(16)).slice(-1);
    return s;
  }
  function add32(a, b) { return (a + b) & 0xFFFFFFFF; }
  function cmn(q, a, b, x, s, t) {
    a = add32(add32(a, q), add32(x, t));
    return add32((a << s) | (a >>> (32 - s)), b);
  }
  function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
  function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
  function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
  function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }
  var str = unescape(encodeURIComponent(input));
  var len = str.length;
  var x = [];
  var i;
  for (i = 0; i < len; i++) x[i >> 2] |= str.charCodeAt(i) << ((i % 4) * 8);
  x[len >> 2] |= 0x80 << ((len % 4) * 8);
  x[(((len + 8) >> 6) << 4) + 14] = len * 8;
  var nwords = ((((len + 8) >> 6) + 1) << 4);
  for (i = 0; i < nwords; i++) { if (x[i] === undefined) x[i] = 0; }
  var a = 1732584193, b = -271733879, c = -1732584194, d = 271733878;
  var S = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
           5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
           4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
           6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21];
  var K = [];
  for (i = 0; i < 64; i++) K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296);
  for (var k = 0; k < x.length; k += 16) {
    var aa = a, bb = b, cc = c, dd = d;
    for (i = 0; i < 64; i++) {
      var f, g;
      if (i < 16) { f = ff; g = i; }
      else if (i < 32) { f = gg; g = (5 * i + 1) % 16; }
      else if (i < 48) { f = hh; g = (3 * i + 5) % 16; }
      else { f = ii; g = (7 * i) % 16; }
      var newB = f(a, b, c, d, x[k + g], S[i], K[i]);
      var tmp = d;
      d = c; c = b; b = newB; a = tmp;
    }
    a = add32(a, aa); b = add32(b, bb); c = add32(c, cc); d = add32(d, dd);
  }
  return rhex(a) + rhex(b) + rhex(c) + rhex(d);
}

// ---------------- 签名（复刻 KuGouMusicApi helper.js） ----------------
// signature = MD5(salt + 排序后"key=value"拼接 + bodyJSON + salt)
//   salt：概念版(lite, appid 3116) = LnT6xpN3khm36zse0QzvmgTZ3waWdRSA
//         主站(main, appid 1005) = OIlwieks28dk2k092lksi2UIkp
var SALT_MAIN = 'OIlwieks28dk2k092lksi2UIkp';
var SALT_LITE = 'LnT6xpN3khm36zse0QzvmgTZ3waWdRSA';

function signatureAndroidParams(params, data, salt) {
  var keys = Object.keys(params).sort();
  var parts = [];
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    var v = params[k];
    parts.push(k + '=' + (typeof v === 'object' ? JSON.stringify(v) : v));
  }
  return md5(salt + parts.join('') + (data || '') + salt);
}

// ---------------- 常量与存储 ----------------
var KEY_CFG = 'kugou_cfg';
var KEY_PROG = 'kugou_progress';
var DEFAULT_UA = 'Android15-1070-11083-46-0-DiscoveryDRADProtocol-wifi';
var LISTEN_UA = 'Android13-1070-10566-201-0-ReportPlaySongToServerProtocol-wifi';
var DEFAULT_AD_ID = 12307537187;
var DEFAULT_MIXSONGID = 666075191;
var MAX_CLAIMS_PER_DAY = 8;
var CLAIMS_PER_RUN = 4;
var CLAIM_GAP_MS = 30000;

function loadCfg() {
  try {
    var s = $persistentStore.read(KEY_CFG);
    return s ? JSON.parse(s) : null;
  } catch (e) { return null; }
}
function saveCfg(cfg) { $persistentStore.write(JSON.stringify(cfg), KEY_CFG); }
function loadProg() {
  try {
    var s = $persistentStore.read(KEY_PROG);
    return s ? JSON.parse(s) : null;
  } catch (e) { return null; }
}
function saveProg(p) { $persistentStore.write(JSON.stringify(p), KEY_PROG); }

function todayStr() {
  var d = new Date();
  function p(n) { return (n < 10 ? '0' : '') + n; }
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}

function ensureDeviceIds(cfg) {
  if (cfg.dfid && !cfg.mid) cfg.mid = md5(cfg.dfid) + md5(cfg.dfid).slice(0, 7);
  if (cfg.dfid && cfg.mid && !cfg.uuid) cfg.uuid = md5(cfg.dfid + cfg.mid);
  return cfg;
}

// ---------------- 请求构造（复刻 KuGouMusicApi request.js） ----------------
// 默认 query：dfid / mid / uuid / appid / clientver / userid / clienttime，
// 有 token 再加 token；extraParams 会覆盖默认值（如听歌接口 clientver=10566）。
// headers：dfid / clienttime / mid + User-Agent（+ POST 时 Content-Type）。
function buildRequest(cfg, method, baseURL, path, extraParams, dataObj, ua, contentType) {
  var clienttime = Math.floor(Date.now() / 1000);
  var params = {
    dfid: cfg.dfid || '-',
    mid: cfg.mid || '',
    uuid: cfg.uuid || '',
    appid: cfg.appid || '',
    clientver: cfg.clientver || '',
    userid: cfg.userid || 0,
    clienttime: clienttime
  };
  if (cfg.token) params.token = cfg.token;
  if (extraParams) {
    for (var k in extraParams) params[k] = extraParams[k];
  }
  var dataStr = dataObj ? JSON.stringify(dataObj) : '';
  var salt = cfg.salt === 'lite' ? SALT_LITE : SALT_MAIN;
  params.signature = signatureAndroidParams(params, dataStr, salt);
  var qs = Object.keys(params).map(function (key) {
    return encodeURIComponent(key) + '=' + encodeURIComponent(String(params[key]));
  }).join('&');
  var headers = {
    'dfid': params.dfid,
    'clienttime': params.clienttime,
    'mid': params.mid,
    'User-Agent': ua
  };
  if (contentType) headers['Content-Type'] = contentType;
  return { url: baseURL + path + '?' + qs, headers: headers, body: dataStr, method: method };
}

// ---------------- $httpClient 封装 ----------------
function httpPost(req) {
  return new Promise(function (resolve) {
    $httpClient.post({ url: req.url, headers: req.headers, body: req.body }, function (error, response, data) {
      if (error) { resolve({ ok: false, error: String(error) }); return; }
      var body = null;
      try { body = JSON.parse(data); } catch (e) { body = null; }
      resolve({ ok: true, status: response && response.status, body: body, raw: data });
    });
  });
}
function httpGet(req) {
  return new Promise(function (resolve) {
    $httpClient.get({ url: req.url, headers: req.headers }, function (error, response, data) {
      if (error) { resolve({ ok: false, error: String(error) }); return; }
      var body = null;
      try { body = JSON.parse(data); } catch (e) { body = null; }
      resolve({ ok: true, status: response && response.status, body: body, raw: data });
    });
  });
}
function sleep(ms) {
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

// 统一解析接口返回：status===1 成功；否则按 error_code 分类。
function parseResult(r, okMsg) {
  if (!r.ok) return { ok: false, msg: '网络错误' + (r.error ? '（' + r.error + '）' : '') };
  var b = r.body;
  if (!b || typeof b !== 'object') return { ok: false, msg: '返回非 JSON' };
  if (b.status === 1) return { ok: true };
  var code = b.error_code || b.errcode || b.code;
  if (code === 30002) return { ok: false, noChance: true, msg: '今日次数已用完' };
  if (code === 130012) return { ok: false, already: true, msg: '今日已领取' };
  return { ok: false, msg: String(b.error || b.msg || b.message || ('status=' + b.status + ' code=' + code)) };
}

// ---------------- 三个接口 ----------------
// 1. 领 VIP：POST https://gateway.kugou.com/youth/v1/ad/play_report
//    body：{ad_id, play_end: 现在, play_start: 现在-30000}（模拟看完 30 秒广告）
function claimOnce(cfg) {
  var now = Date.now();
  var dataObj = {
    ad_id: cfg.ad_id || DEFAULT_AD_ID,
    play_end: now,
    play_start: now - 30000
  };
  var req = buildRequest(cfg, 'POST', 'https://gateway.kugou.com', '/youth/v1/ad/play_report',
    null, dataObj, cfg.ua || DEFAULT_UA, 'application/json');
  return httpPost(req).then(function (r) { return parseResult(r); });
}

// 2. 听歌任务：POST https://gateway.kugou.com/youth/v2/report/listen_song
//    query 覆盖 clientver=10566；专用 UA；body：{mixsongid}
function listenOnce(cfg) {
  var dataObj = { mixsongid: cfg.mixsongid || DEFAULT_MIXSONGID };
  var req = buildRequest(cfg, 'POST', 'https://gateway.kugou.com', '/youth/v2/report/listen_song',
    { clientver: 10566 }, dataObj, LISTEN_UA, 'application/json; charset=utf-8');
  return httpPost(req).then(function (r) { return parseResult(r); });
}

// 3. VIP 到期查询（不影响主流程，失败也无所谓）：
//    GET https://kugouvip.kugou.com/v1/get_union_vip?busi_type=concept
//    到期时间在 data.busi_vip[0].vip_end_time
function vipDetail(cfg) {
  var req = buildRequest(cfg, 'GET', 'https://kugouvip.kugou.com', '/v1/get_union_vip',
    { busi_type: 'concept' }, null, cfg.ua || DEFAULT_UA, null);
  return httpGet(req).then(function (r) {
    if (!r.ok || !r.body) return { ok: false };
    var b = r.body;
    var list = b.data && b.data.busi_vip;
    if (b.status === 1 && list && list.length) {
      return { ok: true, expiry: list[0].vip_end_time || '' };
    }
    return { ok: false };
  });
}

// ---------------- 抓包分支（http-request） ----------------
function parseQuery(url) {
  var q = {};
  var qi = url.indexOf('?');
  if (qi < 0) return q;
  var parts = url.slice(qi + 1).split('&');
  for (var i = 0; i < parts.length; i++) {
    var kv = parts[i].split('=');
    if (kv.length < 2) continue;
    var k = kv[0];
    var v = kv.slice(1).join('=');
    try { v = decodeURIComponent(v); } catch (e) {}
    q[k] = v;
  }
  return q;
}
function parseCookie(header) {
  var ck = {};
  if (!header) return ck;
  var parts = String(header).split(';');
  for (var i = 0; i < parts.length; i++) {
    var pair = parts[i].trim();
    var eq = pair.indexOf('=');
    if (eq <= 0) continue;
    var k = pair.slice(0, eq).trim();
    var v = pair.slice(eq + 1).trim();
    try { v = decodeURIComponent(v); } catch (e) {}
    ck[k] = v;
  }
  return ck;
}

function runCapture() {
  var url = $request.url || '';
  var headers = $request.headers || {};
  var body = $request.body || '';
  var q = parseQuery(url);
  var cookieHeader = headers['Cookie'] || headers['cookie'] || '';
  var ck = parseCookie(cookieHeader);

  var oldCfg = loadCfg() || {};
  var oldToken = oldCfg.token || '';
  var cfg = oldCfg;
  cfg.dfid = q.dfid || ck.dfid || cfg.dfid || '-';
  cfg.userid = q.userid || ck.userid || cfg.userid || 0;
  cfg.token = q.token || ck.token || cfg.token || '';
  cfg.appid = q.appid || cfg.appid || '';
  cfg.clientver = q.clientver || cfg.clientver || '';
  cfg.mid = q.mid || cfg.mid || '';
  cfg.uuid = q.uuid || cfg.uuid || '';
  cfg.ua = headers['User-Agent'] || headers['user-agent'] || cfg.ua || '';
  try {
    var b = JSON.parse(body);
    if (b && b.ad_id) cfg.ad_id = b.ad_id;
    if (b && b.mixsongid) cfg.mixsongid = b.mixsongid;
  } catch (e) {}
  ensureDeviceIds(cfg);

  // 签名自校验：用截到的 query（去掉 signature）+ 原始 body 重算签名，
  // 与截到的 signature 对比，确认盐（main/lite）选对了、签名算法没错。
  var sigOk = false;
  var sigSalt = '';
  var sig = q.signature || '';
  if (sig) {
    var params = {};
    for (var k in q) { if (k !== 'signature') params[k] = q[k]; }
    var salts = String(cfg.appid) === '3116' ? ['lite', 'main'] : ['main', 'lite'];
    for (var i = 0; i < salts.length; i++) {
      var s = signatureAndroidParams(params, body, salts[i] === 'lite' ? SALT_LITE : SALT_MAIN);
      if (s === sig) { sigOk = true; sigSalt = salts[i]; break; }
    }
  }
  if (sigSalt) cfg.salt = sigSalt;
  else if (!cfg.salt) cfg.salt = String(cfg.appid) === '3116' ? 'lite' : 'main';
  cfg.sig_ok = sigOk ? 1 : 0;
  cfg.captured_at = Date.now();
  saveCfg(cfg);

  // 只有 token 变了（或第一次抓到）才弹通知，避免每次打开 App 都刷屏。
  if (cfg.token && cfg.token !== oldToken) {
    $notification.post('酷狗概念版签到',
      'Token 已抓取' + (sigOk ? '（签名自校验通过，' + cfg.salt + '）' : '（签名未校验通过，暂按 ' + cfg.salt + ' 尝试）'),
      'appid ' + (cfg.appid || '?') + ' · userid ' + String(cfg.userid).slice(0, 6) + '***\n' +
      '请在 Surge 模块里关闭「酷狗概念版抓包」，只保留两个定时任务。');
  }
  $done({});
}

// ---------------- 定时分支（cron） ----------------
async function runCron() {
  var cfg = loadCfg();
  if (!cfg || !cfg.token) {
    $notification.post('酷狗概念版签到', '未抓取到 token，今日跳过',
      '请先在概念版 App 里点一次「天天签到领VIP」抓 token，\n抓到后再等下次定时执行。');
    $done();
    return;
  }
  ensureDeviceIds(cfg);
  saveCfg(cfg);

  var today = todayStr();
  var prog = loadProg();
  if (!prog || prog.date !== today) prog = { date: today, listen: 0, claims: 0, stopped: 0 };
  var lines = [];
  var didWork = false;

  if (prog.stopped) {
    // 今日已无次数，本轮什么都不做，也不弹通知。
    $done();
    return;
  }

  // 听歌任务（每天 1 次）
  if (!prog.listen) {
    didWork = true;
    var lr = await listenOnce(cfg);
    if (lr.ok) { prog.listen = 1; lines.push('听歌任务：成功'); }
    else if (lr.already) { prog.listen = 1; lines.push('听歌任务：今日已领取'); }
    else if (lr.noChance) { prog.listen = 1; lines.push('听歌任务：今日无次数'); }
    else { lines.push('听歌任务：失败（' + lr.msg + '）'); }
    saveProg(prog);
  } else {
    lines.push('听歌任务：今日已完成');
  }

  // 领 VIP：每轮最多 4 次，两次间隔 30 秒；全天最多 8 次。
  var target = Math.min(MAX_CLAIMS_PER_DAY, prog.claims + CLAIMS_PER_RUN);
  while (prog.claims < target) {
    didWork = true;
    var cr = await claimOnce(cfg);
    if (cr.ok) {
      prog.claims += 1;
      lines.push('领 VIP 第 ' + prog.claims + ' 次：成功');
      saveProg(prog);
      if (prog.claims < target) await sleep(CLAIM_GAP_MS);
    } else if (cr.noChance || cr.already) {
      prog.stopped = 1;
      lines.push('领 VIP：' + cr.msg + '（今日停止）');
      saveProg(prog);
      break;
    } else {
      lines.push('领 VIP 第 ' + (prog.claims + 1) + ' 次：失败（' + cr.msg + '），本轮停止');
      saveProg(prog);
      break;
    }
  }
  if (prog.claims >= MAX_CLAIMS_PER_DAY) lines.push('今日 8 次已领完');
  else if (!prog.stopped && didWork) lines.push('本轮累计 ' + prog.claims + ' / 8 次，下一轮继续');

  if (!didWork) { $done(); return; }

  // VIP 到期查询（不影响主流程）
  var vip = await vipDetail(cfg);
  var foot = (vip.ok && vip.expiry) ? ('VIP 到期：' + vip.expiry) : 'VIP 到期：未获取到（不影响领取）';
  saveProg(prog);
  $notification.post('酷狗概念版签到 ' + today,
    '听歌 ' + (prog.listen ? '✓' : '✗') + ' · 领 VIP ' + prog.claims + '/8',
    lines.join('\n') + '\n' + foot);
  $done();
}

// ---------------- 入口 ----------------
if (typeof $request !== 'undefined' && $request && $request.url) {
  runCapture();
} else {
  runCron();
}
