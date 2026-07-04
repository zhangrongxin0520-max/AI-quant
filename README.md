# AI-quant

中芯国际（688981.SH）近一年交易数据可视化面板。

## 内容

- **K线图** — 蜡烛图 + MA5/MA20/MA60 均线
- **成交量图** — 与K线联动的柱状图（A股配色：涨红跌绿）
- **统计概览** — 最新价格、涨跌幅、52周高低、日均成交量等

## 数据来源

- Tushare 金融数据接口
- 时间范围：2025-07-04 ~ 2026-07-03（236个交易日）

## 在线浏览

[GitHub Pages](https://zhangrongxin0520-max.github.io/AI-quant/)

## 本地运行

```bash
# 克隆仓库
git clone https://github.com/zhangrongxin0520-max/AI-quant.git
cd AI-quant

# 直接用浏览器打开
open smic_dashboard.html
```

## 文件说明

| 文件 | 说明 |
|---|---|
| `smic_dashboard.html` | 可视化面板（内嵌数据，单文件即可运行） |
| `smic_daily.json` | 原始数据（JSON格式） |
| `smic_daily.csv` | 原始数据（CSV格式，可用Excel打开） |
| `fetch_smic.py` | 数据获取脚本 |
