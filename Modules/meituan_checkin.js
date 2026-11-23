// 美团签到：外卖神券天天领
// 改编自 Euphoriawen/actions-mtz-coupons（MIT）
// - 打开美团 App / 小程序浏览一次，自动保存 token（无需手动复制）
// - 每天 11:05 自动领神券（gundamGrabV4）
// 注意：token 过期后需重新打开美团浏览一次；App 内「我的-每日签到」是另一个接口，不在本次范围
var TOKEN_KEY = 'meituan_token';
var GUNDAM_ID = '2KAWnD';
var UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1';
var HOST = 'https://mediacps.meituan.com';

function http(method, url, headers, body) {
  return new Promise(function (resolve, reject) {
    var opt = { url: url, headers: headers || {} };
    if (!opt.headers['User-Agent']) opt.headers['User-Agent'] = UA;
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

function strField(s, re) {
  var m = s.match(re);
  return m ? m[1] : '';
}
function arrField(s, re) {
  var m = s.match(re);
  if (!m) return [];
  try { return JSON.parse(m[1]); } catch (e) { return []; }
}
function parseMeta(chunk) {
  var moduleId = strField(chunk, /moduleId\s*:\s*"([^"]+)"/);
  var instanceID = strField(chunk, /instanceID\s*:\s*"([^"]+)"/);
  if (!instanceID && moduleId) {
    var f = moduleId.match(/(\d+\.\d+)/);
    if (f) instanceID = f[1];
  }
  return {
    moduleId: moduleId,
    instanceID: instanceID,
    expandCouponIds: arrField(chunk, /expandCouponIds\s*:\s*\{\s*keys\s*:\s*(\[[^\]]*\])/),
    priorityCouponIds: arrField(chunk, /priorityCouponIds\s*:\s*\{\s*keys\s*:\s*(\[[^\]]*\])/),
    cubeToken: strField(chunk, /cubeToken\s*:\s*"([^"]*)"/),
    isStopTJCoupon: /isStopTJCoupon\s*:\s*true/.test(chunk)
  };
}

function notify(title, sub) {
  $notification.post('美团签到', title, String(sub || '').slice(0, 200));
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
  // 2. 活动配置
  var tpl = await http('GET', 'https://market.waimai.meituan.com/api/template/get?env=current&el_biz=waimai&el_page=gundam.loader&gundam_id=' + GUNDAM_ID, { 'Cookie': cookieHeader(token) });
  absorbCookies(tpl.headers);
  var mGlobal = tpl.data.match(/globalData: (\{.+\})/);
  var mAppJs = tpl.data.match(/https:\/\/[./_\-\w]+app\.js(?=")/g);
  if (!mGlobal || !mAppJs || !mAppJs.length) throw new Error('活动配置获取失败');
  var globalData = JSON.parse(mGlobal[1]);
  var gundamId = globalData.gdId || GUNDAM_ID;
  // 3. renderinfo
  var ri = await http('GET', 'https://market.waimai.meituan.com/gd/zc/renderinfo?el_biz=waimai&el_page=gundam.loader&gdId=' + gundamId + '&tenant=gundam', { 'Cookie': cookieHeader(token) });
  absorbCookies(ri.headers);
  var riJson = JSON.parse(ri.data);
  var renderIds = Object.keys(riJson.data || {}).filter(function (k) { return riJson.data[k].render; });
  // 4. app.js 解析 payload
  var appJs = await http('GET', mAppJs[0], {});
  var meta = null;
  for (var i = 0; i < renderIds.length; i++) {
    var re = new RegExp('red-envelope-' + renderIds[i] + '.+?(?=isOtherToAPP)');
    var res = appJs.data.match(re);
    if (res) { meta = parseMeta(res[0]); if (meta && (meta.expandCouponIds.length || meta.priorityCouponIds.length)) break; }
  }
  if (!meta) throw new Error('Payload 解析失败');
  // 5. 领券
  var payload = {
    actualLatitude: 0,
    actualLongitude: 0,
    app: -1,
    platform: 3,
    couponAllConfigIdOrderString: (meta.expandCouponIds || []).join(','),
    couponConfigIdOrderCommaString: (meta.priorityCouponIds || []).join(','),
    gundamId: gundamId,
    instanceId: meta.instanceID || '',
    h5Fingerprint: '',
    rubikCouponKey: meta.cubeToken || '',
    needTj: !!meta.isStopTJCoupon
  };
  var grab = await http('POST', HOST + '/gundam/gundamGrabV4',
    { 'Cookie': cookieHeader(token), 'Content-Type': 'application/json', 'Origin': 'https://market.waimai.meituan.com', 'Referer': 'https://market.waimai.meituan.com/' },
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
  $done();
}

if (typeof $request !== 'undefined' && $request) {
  // 抓包：从美团请求里保存 token
  try {
    var cookie = ($request.headers && ($request.headers['Cookie'] || $request.headers['cookie'])) || '';
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
