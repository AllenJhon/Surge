# Surge 图标合集

一个合集，8 个上游图标库合并而成，3,493 个图标（去重后）。

## 在 Surge 里订阅

策略组 → 图标 → 添加外部图标库，填入：

https://raw.githubusercontent.com/AllenJhon/surge/main/Surge-Icons.json

## 上游来源

- 整合图标合集（weigeshen，含 ①–⑭ 分类）
- fmz200の图标合集
- 图标合集 QureColor
- 黑白图标集 Quremini
- 透明图标集 QureLight-All
- 离歌图标集（注：原作者说链接已更换，此为旧链接）
- 可莉的旗帜图标
- EMBY图标集

合并规则：按上面顺序，重名图标留第一个。

## 更新

每天自动拉取上游重新合并，有变化就更新本文件。

## 模块

### 爱奇艺去广告-修复版

基于可莉的爱奇艺去广告（2026-10-02），只去掉了一条规则：`DOMAIN,api.iqiyi.com,REJECT`。原版这条规则会拦掉爱奇艺的主接口，导致打开爱奇艺时首页加载失败；其余规则、重写和 MITM 与原版一致。

安装链接（Surge → 模块 → + → 粘贴链接）：

https://raw.githubusercontent.com/AllenJhon/surge/main/iQiYi_remove_ads_fixed.sgmodule

装完之后，记得把原来的「爱奇艺去广告」关掉，不然原版那条规则还在拦。
