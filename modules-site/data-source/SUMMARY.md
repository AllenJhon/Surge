# 上游数据摘要 (son.zhiaon.top/data/modules.json)

- 模块总数：1511
- 数据最新更新时间（max updatedAt）：2026-11-27T11:24:01Z
- 去重作者数：111
- 带面板模块：133
- 健康状态：{'unknown': 894, 'ok': 617}

## 失效模块排除（1 个，不发布）

判定方式：链接存活检测（见 data-source/url_audit.json），而非更新时间——上游全部 1511 条的 updatedAt 都在 2026-11，时间上看不出新旧，所以失效与否以模块实际加载的外部资源是否还活着为准。
排除规则：全部外部资源 URL 均已失效，或仓库地址 404；仅含规则、无外部资源的模块保留；403/429/401 判为未知（例如 kelee.one 在本机被 Cloudflare 屏蔽），不作失效处理。
- 上游总数 1511 个，发布 1510 个。

- apple-news-2（Apple News）：唯一的外部资源 URL 已失效：RULE-SET https://raw.githubusercontent.com/DivineEngine/Profiles/master/Surge/Ruleset/Extra/Apple/News.list 返回 404；模块本身除此规则集外无任何内容（仓库 https://github.com/Cyberenchanter/surge-scripts 正常）

## 分类统计

- 广告拦截：989
- 网络工具：165
- 脚本增强：106
- Apple 服务：78
- 应用解锁：66
- 流媒体：59
- 字幕翻译：19
- 规则分流：18
- 应用净化：11

## Top 作者

- 奶思：719
- bit-kitchen：53
- zqzess：43
- NSRingo：41
- nuvora-f44c84：35
- Black-Magic-Lab：35
- Yu9191：31
- VirgilClyne：27
- Rabbit-Spec：27
- gsons：26
- BlackSpacee：25
- NobyDa：22
- yxjxx：21
- mickeu：20
- 许舟：19

## Top 标签

- 去广告：875
- 重写：378
- 视频：224
- 解锁：154
- 面板：141
- 社交：104
- 定时任务：94
- 电商：91
- 签到：64
- DNS：50
- 出行：36
- 银行支付：23
- 反追踪：22
- 音乐：22
- 运营商：12
- 阅读：7
- 地图导航：5
- 游戏：4
