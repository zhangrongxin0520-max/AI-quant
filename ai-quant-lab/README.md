# AI Quant Lab — 交互式技术指标分析工具

纯前端 HTML 单文件应用，内置中芯国际 / 比亚迪 / 长江电力三只股票的日线数据（2025-01-02 ~ 2026-07-03）。

## 快速开始

```bash
# 双击打开
open indicator_tool.html

# 或部署到静态服务器
python -m http.server 8080
```

## 功能

| 功能 | 说明 |
|------|------|
| 股票切换 | 下拉菜单选择中芯国际 / 比亚迪 / 长江电力 |
| 时间范围 | 全部 / 1月 / 3月 / 6月 / 1年 |
| BOLL 参数 | 周期 N (2-50) + 倍数 K (1.0-4.0)，滑块实时调节 |
| RSI 参数 | 周期 N (2-50)，含 70/30 超买超卖线 |
| MACD 参数 | 快线(2-50) / 慢线(5-100) / 信号线(2-30) |
| 主图 | K线蜡烛图 + 布林带上中下轨 + MA5/MA10/MA20/MA60 |
| 副图 | RSI 线 + MACD柱/DIF/DEA |

## 文件结构

```
ai-quant-lab/
├── indicator_tool.html   # 主应用（内嵌全部数据，双击即用）
├── gen_tool.py           # 生成脚本（从CSV构建HTML）
├── data/
│   ├── smic_daily.csv    # 中芯国际 688981.SH
│   ├── byd_daily.csv     # 比亚迪   002594.SZ
│   └── cjdl_daily.csv    # 长江电力 600900.SH
└── README.md
```

## 技术栈

- ECharts 5.5（CDN）
- 原生 HTML/CSS/JS（零框架依赖）
- 数据嵌入 HTML（离线可用）

## 开发

```bash
# 修改 gen_tool.py 后重新生成 HTML
python gen_tool.py
```
