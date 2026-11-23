// 美团签到：外卖神券天天领 v5
// 改编自 Euphoriawen/actions-mtz-coupons（MIT），按 2026-11 美团活动页新版改写
// - 打开美团 App / 小程序浏览一次，自动保存 token（无需手动复制）
// - 每天 11:05 自动领神券（gundamGrabV4）
// 注意：token 过期后需重新打开美团浏览一次；App 内「我的-每日签到」是另一个接口，不在本次范围
// v2 改动：模板接口已改版，不再返回带 app.js 链接的页面，券配置改走 POST /component/instanceProps。
// v3 改动：模板接口在真机上会被美团反爬拦截（302 到 verify.meituan.com 验证页），
//   因此默认跳过模板调用，直接用活动 id（2026-11-23 从加载器实测：gdId 531693，pageId 536482）；
//   只有硬编码 id 取不到组件时才回退到模板接口。
//   同时抓取真实的 webview UA 一起保存，API 请求用它代替 Safari UA，减少被风控的可能。
// v4 改动：instanceProps 返回空数据。分析页面 bundle 发现组件配置的首选来源是
//   模板响应 globalData 里的 instanceProps / renderTree（有会话时服务端才会填充），
//   因此先用已抓到的真实 UA 调一次模板接口，整段 globalData 里递归找券配置；
//   模板被拦截或无券数据时再回退到 v3 路径（renderinfo + instanceProps，改传全部组件 id）。
// v5 改动：v4 实测两条路都走不通——模板即使带真实 UA 仍被反爬拦截，
//   instanceProps 即使带 token、传全部组件 id 也返回空数据。
//   结论：脚本主动调接口拿不到券配置，但页面自己在 App 里打开时一定拿到了。
//   因此改抓包：用 http-response 脚本直接读取页面自己的模板/instanceProps 响应，
//   把券配置保存下来，定时任务只读保存好的配置去领券，不再主动调那两个接口。
var VERSION = 'v5';
var TOKEN_KEY = 'meituan_token';
var UA_KEY = 'meituan_ua';
var META_KEY = 'meituan_coupon_meta';
var GUNDAM_ID = 531693;
var PAGE_ID = 536482;
var UA_FALLBACK = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1';
var HOST = 'https://mediacps.meituan.com';
var MARKET = 'https://market.waimai.meituan.com';

function ua() {
  return $persistentStore.read(UA_KEY) || UA_FALLBACK;
}

function http(method, url, headers, body) {
  return new Promise(function (resolve, reject) {
    var opt = { url: url, headers: headers || {} };
    if (!opt.headers['User-Agent']) opt.headers['User-Agent'] = ua();
    if (body !== undefined && body !== null) opt.body = body;
    $httpClient[method.toLowerCase()](opt, function (err, resp, data) {
      if (err) return reject(err);
      resolve({ status: resp.status, headers: resp.headers || {}, data: data || '' });
    });
  });
}

// 简单 cookie 累积：把响应 Set-Cookie 里的 key=value 拼进后续请求
var extraCookie = '';
function absorbCookies(headers) {
  var sc = headers['Set-Cookie'] || headers['set-cookie'];
  if (!sc) return;
  var list = Array.isArray(sc) ? sc : [sc];
  list.forEach(function (c) {
    var kv = String(c).split(';')[0].trim();
    if (kv) extraCookie += (extraCookie ? '; ' : '') + kv;
  });
}
function cookieHeader(token) {
  return 'token=' + token + (extraCookie ? '; ' + extraCookie : '');
}

// 从文本中提取 marker 后的第一个配对花括号 JSON（可跨行，正确处理字符串与转义）
function extractJsonAfter(text, marker) {
  var i = text.indexOf(marker);
  if (i < 0) return null;
  var start = text.indexOf('{', i);
  if (start < 0) return null;
  var depth = 0, inStr = false, esc = false;
  for (var j = start; j < text.length; j++) {
    var c = text[j];
    if (inStr) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === '"') inStr = false;
    } else {
      if (c === '"') inStr = true;
      else if (c === '{') depth++;
      else if (c === '}') {
        depth--;
        if (depth === 0) {
          try { return JSON.parse(text.slice(start, j + 1)); } catch (e) { return null; }
        }
      }
    }
  }
  return null;
}

// 在 instanceProps / globalData 里递归找券配置：
// 形如 {expandCouponIds:{keys:[...]}, priorityCouponIds:{keys:[...]}, cubeToken, instanceID}
// 或 keys 里含 coupon 的数组；返回 {instanceId, expand, priority, cubeToken}
function findCouponData(node, topKey, out) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    for (var i = 0; i < node.length; i++) findCouponData(node[i], topKey, out);
    return;
  }
  var keys = Object.keys(node);
  var hasExpand = node.expandCouponIds && node.expandCouponIds.keys;
  var hasPriority = node.priorityCouponIds && node.priorityCouponIds.keys;
  var cube = node.cubeToken || node.rubikCouponKey || '';
  if (hasExpand || hasPriority) {
    out.found = {
      instanceId: node.instanceID || node.instanceId || topKey || '',
      expand: hasExpand ? node.expandCouponIds.keys : [],
      priority: hasPriority ? node.priorityCouponIds.keys : [],
      cubeToken: cube || '',
      isStopTJCoupon: !!node.isStopTJCoupon
    };
    return;
  }
  // 兜底：直接挂在对象上的券 id 数组
  for (var k = 0; k < keys.length; k++) {
    var key = keys[k];
    var v = node[key];
    if (Array.isArray(v) && v.length && /coupon/i.test(key) && typeof v[0] !== 'object') {
      out.found = {
        instanceId: node.instanceID || node.instanceId || topKey || '',
        expand: v,
        priority: [],
        cubeToken: cube || '',
        isStopTJCoupon: !!node.isStopTJCoupon
      };
      return;
    }
  }
  for (var k2 = 0; k2 < keys.length; k2++) {
    findCouponData(node[keys[k2]], topKey, out);
    if (out.found) return;
  }
}

function notify(title, sub) {
  $notification.post('美团签到', title, String(sub || '').slice(0, 190) + ' [' + VERSION + ']');
}

// 从一处数据源里找券配置并保存（带保存日期，每天首次打开页面会刷新）
function saveMetaFrom(node, gundamId, pageId) {
  var out = { found: null };
  findCouponData(node, '', out);
  if (!out.found) return false;
  var meta = out.found;
  meta.gundamId = gundamId || GUNDAM_ID;
  meta.pageId = pageId || PAGE_ID;
  var today = new Date();
  meta.savedDate = today.getFullYear() + '-' + (today.getMonth() + 1) + '-' + today.getDate();
  var prev = $persistentStore.read(META_KEY) || '';
  var next = JSON.stringify(meta);
  if (prev !== next) {
    $persistentStore.write(next, META_KEY);
    notify('券配置已保存', '今天打开神券页时已抓到，明天 11:05 自动领');
  }
  return true;
}

function loadMeta() {
  try {
    var raw = $persistentStore.read(META_KEY);
    if (!raw) return null;
    var meta = JSON.parse(raw);
    var today = new Date();
    var todayStr = today.getFullYear() + '-' + (today.getMonth() + 1) + '-' + today.getDate();
    if (meta.savedDate !== todayStr) return null; // 不是今天的，作废
    return meta;
  } catch (e) { return null; }
}

async function doGrab(token, gundamId, meta) {
  var payload = {
    actualLatitude: 0,
    actualLongitude: 0,
    app: -1,
    platform: 3,
    couponAllConfigIdOrderString: (meta.expand || []).join(','),
    couponConfigIdOrderCommaString: (meta.priority || []).join(','),
    gundamId: gundamId,
    instanceId: meta.instanceId || '',
    h5Fingerprint: '',
    rubikCouponKey: meta.cubeToken || '',
    needTj: !!meta.isStopTJCoupon
  };
  var grab = await http('POST', HOST + '/gundam/gundamGrabV4',
    { 'Cookie': cookieHeader(token), 'Content-Type': 'application/json', 'Origin': MARKET, 'Referer': MARKET + '/' },
    JSON.stringify(payload));
  var grabJson = JSON.parse(grab.data);
  if (grabJson.code === 0) {
    var coupons = (grabJson.data && grabJson.data.coupons) || [];
    var text = coupons.length
      ? coupons.map(function (c) { return '￥' + c.couponAmount + '（' + c.amountLimit + '）'; }).join('\n')
      : '今日已领过';
    notify('神券领取成功', text);
  } else if (grabJson.code === 3) {
    notify('Token 已过期', '重新打开美团 App 浏览一次');
  } else {
    notify('领券失败', grabJson.msg || grabJson.message || ('code ' + grabJson.code));
  }
}

async function main() {
  var token = $persistentStore.read(TOKEN_KEY);
  if (!token) {
    notify('还没有 Token', '打开美团 App 浏览一次，自动保存');
    return $done();
  }
  // 1. 检查登录
  var login = await http('POST', HOST + '/gundam/gundamLogin', { 'Cookie': cookieHeader(token) }, '');
  absorbCookies(login.headers);
  var loginJson;
  try { loginJson = JSON.parse(login.data); } catch (e) { throw new Error('登录接口返回异常'); }
  if (loginJson.code === 3) {
    notify('Token 已过期', '重新打开美团 App 浏览一次');
    return $done();
  }
  if (loginJson.code !== 0) throw new Error('登录检查失败: ' + (loginJson.msg || loginJson.message || loginJson.code));
  // 2. 只用抓包保存好的券配置领券，不再主动调模板/instanceProps 接口
  var meta = loadMeta();
  if (!meta) {
    notify('还没有券配置', '打开一次美团神券页，自动保存后再领');
    return $done();
  }
  await doGrab(token, meta.gundamId || GUNDAM_ID, meta);
  $done();
}

// http-response：读取页面自己的模板 / instanceProps 响应，把券配置保存下来
function handleResponse() {
  try {
    var url = ($request.url || '');
    var body = ($response.body || '');
    if (!body) return;
    if (url.indexOf('template/get') >= 0) {
      var gd = extractJsonAfter(body, 'globalData:');
      if (!gd) return;
      if (gd.instanceProps) saveMetaFrom(gd.instanceProps, gd.gdId, gd.pageId);
      if (gd.renderTree) saveMetaFrom(gd.renderTree, gd.gdId, gd.pageId);
    } else if (url.indexOf('instanceProps') >= 0) {
      var propsJson = JSON.parse(body);
      var propsData = propsJson.data || {};
      var keys = Object.keys(propsData);
      for (var i = 0; i < keys.length; i++) {
        if (saveMetaFrom(propsData[keys[i]], GUNDAM_ID, PAGE_ID)) break;
      }
    }
  } catch (e) {}
}

if (typeof $response !== 'undefined' && $response) {
  handleResponse();
  $done({});
} else if (typeof $request !== 'undefined' && $request) {
  // 抓包：从美团请求里保存 token，同时保存真实的 webview UA 供 API 请求使用
  try {
    var headers = $request.headers || {};
    var cookie = headers['Cookie'] || headers['cookie'] || '';
    var reqUa = headers['User-Agent'] || headers['user-agent'] || '';
    if (reqUa && $persistentStore.read(UA_KEY) !== reqUa) {
      $persistentStore.write(reqUa, UA_KEY);
    }
    var m = cookie.match(/token=([^;]+)/);
    if (m && m[1] && $persistentStore.read(TOKEN_KEY) !== m[1]) {
      $persistentStore.write(m[1], TOKEN_KEY);
      notify('Token 已保存', '每天 11:05 自动领神券');
    }
  } catch (e) {}
  $done({});
} else {
  main().catch(function (e) {
    notify('领券失败', (e && e.message) || String(e));
    $done();
  });
}
