#!/usr/bin/env python3
"""生成指标分析工具 HTML — 按用户截图布局：左侧参数栏 + 右侧大图"""

import csv, json, pathlib

PROJECT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT / "data" / "daily"
OUTPUT = pathlib.Path(__file__).resolve().parent / "indicator_tool.html"

STOCKS = {
    "smic":  {"name": "中芯国际", "code": "688981"},
    "byd":   {"name": "比亚迪",   "code": "002594"},
    "cjdl":  {"name": "长江电力", "code": "600900"},
}

# ── 加载数据 ──
all_data = {}
for sid, info in STOCKS.items():
    path = DATA_DIR / f"{sid}_daily.csv"
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    records = []
    for r in rows:
        records.append([
            r["trade_date"],       # 0
            float(r["open"]),    # 1
            float(r["high"]),    # 2
            float(r["low"]),     # 3
            float(r["close"]),   # 4
            float(r["vol"]),     # 5
        ])
    all_data[sid] = records

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Indicator Lab Interactive</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
:root {{
  --bg: #f5f5f5;
  --card: #ffffff;
  --text: #333333;
  --muted: #999999;
  --border: #e8e8e8;
  --accent: #3b82f6;
  --boll: #4ade80;
  --rsi: #3b82f6;
  --macd: #f87171;
  --red: #ef4444;
  --green: #22c55e;
  --radius: 8px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--text); min-height:100vh; overflow-x:hidden; }}

/* ── Header ── */
header {{ background:var(--bg); padding:12px 20px; display:flex; align-items:center; gap:12px; border-bottom:1px solid var(--border); }}
header h1 {{ font-size:16px; font-weight:500; color:var(--text); }}
.time-btns {{ display:flex; gap:4px; margin-left:auto; }}
.time-btn {{ background:#fff; border:1px solid var(--border); color:var(--text); padding:4px 12px; border-radius:4px; font-size:12px; cursor:pointer; transition:all 0.15s; }}
.time-btn:hover {{ border-color:var(--accent); }}
.time-btn.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}

/* ── Layout ── */
.container {{ display:flex; gap:12px; padding:12px 20px; max-width:1600px; margin:0 auto; height:calc(100vh - 48px); overflow:hidden; }}
@media (max-width:900px) {{ .container {{ flex-direction:column; height:auto; }} }}

/* ── Left Sidebar ── */
.sidebar {{ width:260px; flex-shrink:0; display:flex; flex-direction:column; gap:10px; overflow-y:auto; }}
@media (max-width:900px) {{ .sidebar {{ width:100%; flex-direction:row; flex-wrap:wrap; }} }}

.card {{ background:var(--card); border-radius:var(--radius); padding:14px; box-shadow:0 1px 3px rgba(0,0,0,0.04); }}
.card-title {{ font-size:12px; font-weight:500; color:var(--muted); margin-bottom:8px; display:flex; align-items:center; gap:4px; }}
.dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

/* Stock selector */
.stock-select {{ width:100%; padding:8px 10px; border:1px solid var(--border); border-radius:6px; font-size:13px; background:#fff; cursor:pointer; outline:none; }}
.stock-select:focus {{ border-color:var(--accent); }}

/* Price info */
.price-row {{ display:flex; align-items:baseline; gap:8px; margin-bottom:6px; }}
.price-main {{ font-size:22px; font-weight:600; }}
.price-change {{ font-size:13px; color:var(--red); font-weight:500; }}
.price-change.down {{ color:var(--green); }}
.price-label {{ font-size:11px; color:var(--muted); }}
.price-range {{ font-size:12px; color:var(--text); margin-top:4px; }}

/* Slider */
.slider-row {{ margin-bottom:12px; }}
.slider-label {{ display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }}
.slider-label .name {{ color:var(--text); }}
.slider-label .val {{ color:var(--accent); font-weight:500; }}
input[type="range"] {{ width:100%; height:4px; -webkit-appearance:none; appearance:none; background:var(--border); border-radius:2px; outline:none; cursor:pointer; }}
input[type="range"]::-webkit-slider-thumb {{ -webkit-appearance:none; width:14px; height:14px; background:var(--accent); border-radius:50%; cursor:pointer; border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,0.2); }}
input[type="range"]::-moz-range-thumb {{ width:14px; height:14px; background:var(--accent); border-radius:50%; cursor:pointer; border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,0.2); }}

/* Summary values */
.summary-row {{ display:flex; gap:12px; margin-top:8px; font-size:12px; }}
.summary-item {{ display:flex; flex-direction:column; gap:2px; }}
.summary-item .num {{ font-size:14px; font-weight:600; }}
.summary-item .lbl {{ font-size:10px; color:var(--muted); }}

/* Status */
.status-row {{ display:flex; align-items:center; gap:6px; font-size:13px; margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }}
.status-dot {{ width:8px; height:8px; border-radius:50%; }}
.status-text {{ color:var(--muted); }}

/* ── Right Main ── */
.main {{ flex:1; display:flex; flex-direction:column; gap:10px; min-width:0; overflow-y:auto; }}
.main-chart {{ background:var(--card); border-radius:var(--radius); box-shadow:0 1px 3px rgba(0,0,0,0.04); padding:10px; }}
.sub-chart {{ background:var(--card); border-radius:var(--radius); box-shadow:0 1px 3px rgba(0,0,0,0.04); padding:10px; height:180px; }}

/* Chart titles */
.chart-title {{ font-size:13px; font-weight:500; margin-bottom:4px; display:flex; align-items:center; gap:6px; }}
.chart-title .dot {{ width:6px; height:6px; }}
.legend {{ display:flex; gap:12px; font-size:11px; color:var(--muted); margin-bottom:4px; flex-wrap:wrap; }}
.legend-item {{ display:flex; align-items:center; gap:3px; }}
.legend-line {{ width:12px; height:2px; border-radius:1px; }}

/* Chart containers */
#mainChart {{ width:100%; height:360px; }}
#rsiChart {{ width:100%; height:140px; }}
#macdChart {{ width:100%; height:140px; }}
</style>
</head>
<body>

<header>
  <h1>Indicator Lab Interactive</h1>
  <div class="time-btns" id="timeBtns">
    <button class="time-btn active" data-range="0">全部</button>
    <button class="time-btn" data-range="21">1月</button>
    <button class="time-btn" data-range="63">3月</button>
    <button class="time-btn" data-range="126">6月</button>
    <button class="time-btn" data-range="250">1年</button>
  </div>
</header>

<div class="container">
  <!-- Left sidebar -->
  <div class="sidebar">
    <!-- Stock card -->
    <div class="card">
      <div class="card-title">选择股票</div>
      <select class="stock-select" id="stockSelect">
        <option value="smic">中芯国际 A · 688981</option>
        <option value="byd">比亚迪 A · 002594</option>
        <option value="cjdl">长江电力 A · 600900</option>
      </select>
      <div id="priceInfo" style="margin-top:10px;">
        <div class="price-row"><span class="price-main" id="latestPrice">--</span><span class="price-change" id="priceChange">--</span></div>
        <div class="price-label" id="priceLabel">收盘价 CNY</div>
        <div class="price-range" id="priceRange">--</div>
      </div>
    </div>

    <!-- BOLL params -->
    <div class="card">
      <div class="card-title"><span class="dot" style="background:var(--boll)"></span>BOLL · 布林带</div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">周期 N</span><span class="val" id="bollNVal">20</span></div>
        <input type="range" id="bollN" min="2" max="50" value="20">
      </div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">倍数 K</span><span class="val" id="bollKVal">2.0</span></div>
        <input type="range" id="bollK" min="1" max="4" step="0.1" value="2.0">
      </div>
      <div class="summary-row" id="bollSummary">
        <div class="summary-item"><span class="num" id="bollUpper">--</span><span class="lbl">上轨</span></div>
        <div class="summary-item"><span class="num" id="bollMid">--</span><span class="lbl">中轨</span></div>
        <div class="summary-item"><span class="num" id="bollLower">--</span><span class="lbl">下轨</span></div>
        <div class="summary-item"><span class="num" id="bollWidth">--</span><span class="lbl">带宽</span></div>
      </div>
    </div>

    <!-- RSI params -->
    <div class="card">
      <div class="card-title"><span class="dot" style="background:var(--rsi)"></span>RSI · 相对强弱指标</div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">周期 N</span><span class="val" id="rsiNVal">14</span></div>
        <input type="range" id="rsiN" min="2" max="50" value="14">
      </div>
      <div class="status-row" id="rsiStatus">
        <span class="status-dot" style="background:var(--rsi)"></span>
        <span class="status-text" id="rsiText">--</span>
      </div>
    </div>

    <!-- MACD params -->
    <div class="card">
      <div class="card-title"><span class="dot" style="background:var(--macd)"></span>MACD · 异同移动平均线</div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">快线 Fast</span><span class="val" id="macdFastVal">12</span></div>
        <input type="range" id="macdFast" min="2" max="50" value="12">
      </div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">慢线 Slow</span><span class="val" id="macdSlowVal">26</span></div>
        <input type="range" id="macdSlow" min="5" max="100" value="26">
      </div>
      <div class="slider-row">
        <div class="slider-label"><span class="name">信号线</span><span class="val" id="macdSigVal">9</span></div>
        <input type="range" id="macdSig" min="2" max="30" value="9">
      </div>
    </div>
  </div>

  <!-- Right main area -->
  <div class="main">
    <div class="main-chart">
      <div class="chart-title">价格走势 · 布林带</div>
      <div class="legend">
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>上轨</span>
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>下轨</span>
        <span class="legend-item"><span class="legend-line" style="background:#378add;"></span>中轨</span>
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>MA5</span>
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>MA10</span>
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>MA20</span>
        <span class="legend-item"><span class="legend-line" style="background:#ccc;"></span>MA60</span>
        <span class="legend-item"><span class="legend-line" style="background:#333;"></span>收盘价</span>
      </div>
      <div id="mainChart"></div>
    </div>
    <div class="sub-chart">
      <div class="chart-title">RSI</div>
      <div id="rsiChart"></div>
    </div>
    <div class="sub-chart">
      <div class="chart-title">MACD</div>
      <div class="legend">
        <span class="legend-item"><span class="legend-line" style="background:#f87171;"></span>MACD Hist</span>
        <span class="legend-item"><span class="legend-line" style="background:#f87171;"></span>DIF</span>
        <span class="legend-item"><span class="legend-line" style="background:#3b82f6;"></span>DEA</span>
      </div>
      <div id="macdChart"></div>
    </div>
  </div>
</div>

<script>
// ===== 嵌入数据 =====
const DATA = {json.dumps(all_data)};
const STOCK_NAMES = {json.dumps({k:v['name'] for k,v in STOCKS.items()})};

// ===== 状态 =====
let currentStock = 'smic';
let currentData = null;
let timeWindow = 0;
let chartMain = null, chartRsi = null, chartMacd = null;

// ===== 工具函数 =====
function getData(sid) {{
  const raw = DATA[sid];
  return raw.map(r => ({{ date: r[0], open: r[1], high: r[2], low: r[3], close: r[4], vol: r[5] }}));
}}
function sliceData(arr, n) {{
  if (!n || n >= arr.length) return arr;
  return arr.slice(arr.length - n);
}}
function fmtDate(d) {{
  return d.slice(0,4) + '-' + d.slice(4,6) + '-' + d.slice(6);
}}

// ===== SMA =====
function calcSMA(arr, n) {{
  const out = new Array(arr.length).fill(null);
  for (let i = n - 1; i < arr.length; i++) {{
    let s = 0;
    for (let j = i - n + 1; j <= i; j++) s += arr[j];
    out[i] = Math.round(s / n * 100) / 100;
  }}
  return out;
}}

// ===== EMA =====
function calcEMA(arr, n) {{
  const a = 2 / (n + 1);
  const out = new Array(arr.length).fill(null);
  let s = 0;
  for (let i = 0; i < n; i++) s += arr[i];
  out[n-1] = s / n;
  for (let i = n; i < arr.length; i++) out[i] = a * arr[i] + (1 - a) * out[i-1];
  return out;
}}

// ===== RSI =====
function calcRSI(closeArr, period) {{
  const N = Math.max(2, period);
  const rsi = new Array(closeArr.length).fill(null);
  let ag = 0, al = 0;
  for (let i = 1; i <= N && i < closeArr.length; i++) {{
    const d = closeArr[i] - closeArr[i-1];
    ag += Math.max(d, 0); al += Math.max(-d, 0);
  }}
  ag /= N; al /= N;
  rsi[N] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  for (let i = N + 1; i < closeArr.length; i++) {{
    const d = closeArr[i] - closeArr[i-1];
    ag = (ag * (N - 1) + Math.max(d, 0)) / N;
    al = (al * (N - 1) + Math.max(-d, 0)) / N;
    rsi[i] = al === 0 ? 100 : Math.round((100 - 100 / (1 + ag / al)) * 100) / 100;
  }}
  const last = rsi[rsi.length - 1];
  const status = last >= 70 ? '超买' : last <= 30 ? '超卖' : '中性';
  return {{ rsi, last, status }};
}}

// ===== MACD =====
function calcMACD(closeArr, fast, slow, sig) {{
  const emaF = calcEMA(closeArr, fast);
  const emaS = calcEMA(closeArr, slow);
  const dif = closeArr.map((_,i) => emaF[i] && emaS[i] ? Math.round((emaF[i]-emaS[i])*10000)/10000 : null);
  const valid = dif.filter(v => v !== null);
  const deaRaw = calcEMA(valid, sig);
  const dea = new Array(closeArr.length).fill(null);
  const offset = slow - 1 + sig - 1;
  for (let i = 0; i < deaRaw.length; i++) if (deaRaw[i] !== null) dea[offset + i] = Math.round(deaRaw[i]*10000)/10000;
  const macdBar = closeArr.map((_,i) => dif[i] && dea[i] ? Math.round(2*(dif[i]-dea[i])*10000)/10000 : null);
  const lastD = dif.filter(v => v).pop() || 0;
  const lastE = dea.filter(v => v).pop() || 0;
  return {{ dif, dea, macdBar, lastDif: lastD, lastDea: lastE }};
}}

// ===== Bollinger =====
function calcBollinger(closeArr, period, k) {{
  const N = Math.max(2, period);
  const upper = [], mid = [], lower = [];
  for (let i = 0; i < closeArr.length; i++) {{
    if (i < N - 1) {{ upper.push(null); mid.push(null); lower.push(null); continue; }}
    const slice = closeArr.slice(i - N + 1, i + 1);
    const m = slice.reduce((a,b)=>a+b,0) / N;
    const v = slice.reduce((a,b)=>a+(b-m)*(b-m),0) / (N-1);
    const s = Math.sqrt(v);
    upper.push(Math.round((m + k*s)*100)/100);
    mid.push(Math.round(m*100)/100);
    lower.push(Math.round((m - k*s)*100)/100);
  }}
  return {{ upper, mid, lower }};
}}

// ===== Render =====
function renderAll() {{
  const d = sliceData(currentData, timeWindow);
  if (!d.length) return;
  const dates = d.map(r => r.date);
  const closes = d.map(r => r.close);
  const candle = d.map(r => [r.open, r.close, r.low, r.high]);
  
  // ── Params ──
  const bollN = +document.getElementById('bollN').value;
  const bollK = +document.getElementById('bollK').value;
  const rsiN = +document.getElementById('rsiN').value;
  const macdFast = +document.getElementById('macdFast').value;
  const macdSlow = +document.getElementById('macdSlow').value;
  const macdSig = +document.getElementById('macdSig').value;
  
  // ── Update left sidebar ──
  const last = d[d.length - 1];
  const prev = d.length > 1 ? d[d.length - 2] : last;
  const change = ((last.close - prev.close) / prev.close * 100);
  const chgStr = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
  document.getElementById('latestPrice').textContent = last.close.toFixed(2);
  const chgEl = document.getElementById('priceChange');
  chgEl.textContent = chgStr;
  chgEl.className = 'price-change' + (change < 0 ? ' down' : '');
  document.getElementById('priceRange').textContent = fmtDate(dates[0]) + ' ~ ' + fmtDate(dates[dates.length-1]);
  
  document.getElementById('bollNVal').textContent = bollN;
  document.getElementById('bollKVal').textContent = bollK;
  document.getElementById('rsiNVal').textContent = rsiN;
  document.getElementById('macdFastVal').textContent = macdFast;
  document.getElementById('macdSlowVal').textContent = macdSlow;
  document.getElementById('macdSigVal').textContent = macdSig;
  
  // ── Indicators ──
  const {{ upper, mid, lower }} = calcBollinger(closes, bollN, bollK);
  const ma5 = calcSMA(closes, 5);
  const ma10 = calcSMA(closes, 10);
  const ma20 = calcSMA(closes, 20);
  const ma60 = calcSMA(closes, 60);
  const {{ rsi, last: lastRsi, status: rsiStatus }} = calcRSI(closes, rsiN);
  const {{ dif, dea, macdBar, lastDif, lastDea }} = calcMACD(closes, macdFast, macdSlow, macdSig);
  
  // BOLL summary
  const lastU = upper[upper.length-1], lastM = mid[mid.length-1], lastL = lower[lower.length-1];
  const bw = lastM ? Math.round((lastU - lastL) / lastM * 1000) / 10 : 0;
  document.getElementById('bollUpper').textContent = lastU ? lastU.toFixed(2) : '--';
  document.getElementById('bollMid').textContent = lastM ? lastM.toFixed(2) : '--';
  document.getElementById('bollLower').textContent = lastL ? lastL.toFixed(2) : '--';
  document.getElementById('bollWidth').textContent = bw ? bw + '%' : '--';
  
  // RSI status
  document.getElementById('rsiText').textContent = lastRsi ? lastRsi.toFixed(1) + ' · ' + rsiStatus : '--';
  
  // ── Main chart (K + Bollinger + MA) ──
  const commonAxis = {{
    type: 'category', data: dates, axisLine: {{ lineStyle: {{ color: '#e8e8e8' }} }},
    axisLabel: {{ fontSize: 10, color: '#999', interval: Math.max(1, Math.floor(dates.length / 8)) }},
    axisTick: {{ show: false }}
  }};
  chartMain.setOption({{
    grid: {{ left: 50, right: 20, top: 10, bottom: 20, containLabel: true }},
    xAxis: [{{ ...commonAxis, axisLabel: {{ show: false }} }}, {{ ...commonAxis }}],
    yAxis: [{{ type: 'value', scale: true, splitLine: {{ lineStyle: {{ color: '#f0f0f0' }} }}, axisLabel: {{ fontSize: 10, color: '#999' }} }}],
    dataZoom: [{{ type: 'inside', xAxisIndex: [0,1] }}],
    series: [
      {{ type: 'candlestick', data: candle, xAxisIndex: 0, yAxisIndex: 0, itemStyle: {{ color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' }} }},
      {{ type: 'line', data: upper, symbol: 'none', lineStyle: {{ color: '#ccc', width: 1, type: 'dashed' }}, name: '上轨' }},
      {{ type: 'line', data: lower, symbol: 'none', lineStyle: {{ color: '#ccc', width: 1, type: 'dashed' }}, name: '下轨' }},
      {{ type: 'line', data: mid, symbol: 'none', lineStyle: {{ color: '#378add', width: 1.5 }}, name: '中轨' }},
      {{ type: 'line', data: ma5, symbol: 'none', lineStyle: {{ color: '#999', width: 0.8 }}, name: 'MA5' }},
      {{ type: 'line', data: ma10, symbol: 'none', lineStyle: {{ color: '#999', width: 0.8 }}, name: 'MA10' }},
      {{ type: 'line', data: ma20, symbol: 'none', lineStyle: {{ color: '#999', width: 0.8 }}, name: 'MA20' }},
      {{ type: 'line', data: ma60, symbol: 'none', lineStyle: {{ color: '#999', width: 0.8 }}, name: 'MA60' }},
    ],
    tooltip: {{ trigger: 'axis' }},
    legend: {{ show: false }},
  }}, true);
  
  // ── RSI chart ──
  chartRsi.setOption({{
    grid: {{ left: 50, right: 20, top: 10, bottom: 20, containLabel: true }},
    xAxis: [{{ ...commonAxis }}],
    yAxis: [{{ type: 'value', min: 0, max: 100, splitLine: {{ lineStyle: {{ color: '#f0f0f0' }} }}, axisLabel: {{ fontSize: 10, color: '#999' }} }}],
    series: [
      {{ type: 'line', data: rsi, symbol: 'none', lineStyle: {{ color: '#3b82f6', width: 1.2 }}, name: 'RSI(' + rsiN + ')' }},
      {{ type: 'line', data: new Array(dates.length).fill(70), symbol: 'none', lineStyle: {{ color: '#ef4444', width: 0.8, type: 'dashed' }}, name: '70' }},
      {{ type: 'line', data: new Array(dates.length).fill(30), symbol: 'none', lineStyle: {{ color: '#22c55e', width: 0.8, type: 'dashed' }}, name: '30' }},
    ],
    tooltip: {{ trigger: 'axis' }},
    legend: {{ show: false }},
  }}, true);
  
  // ── MACD chart ──
  const barColors = macdBar.map(v => v >= 0 ? '#ef4444' : '#22c55e');
  chartMacd.setOption({{
    grid: {{ left: 50, right: 20, top: 10, bottom: 20, containLabel: true }},
    xAxis: [{{ ...commonAxis }}],
    yAxis: [{{ type: 'value', splitLine: {{ lineStyle: {{ color: '#f0f0f0' }} }}, axisLabel: {{ fontSize: 10, color: '#999' }} }}],
    series: [
      {{ type: 'bar', data: macdBar, itemStyle: {{ color: (params) => barColors[params.dataIndex] }}, name: 'MACD Hist' }},
      {{ type: 'line', data: dif, symbol: 'none', lineStyle: {{ color: '#f87171', width: 1 }}, name: 'DIF' }},
      {{ type: 'line', data: dea, symbol: 'none', lineStyle: {{ color: '#3b82f6', width: 1 }}, name: 'DEA' }},
    ],
    tooltip: {{ trigger: 'axis' }},
    legend: {{ show: false }},
  }}, true);
}}

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {{
  chartMain = echarts.init(document.getElementById('mainChart'));
  chartRsi = echarts.init(document.getElementById('rsiChart'));
  chartMacd = echarts.init(document.getElementById('macdChart'));
  currentData = getData(currentStock);
  renderAll();
  
  // Stock change
  document.getElementById('stockSelect').addEventListener('change', (e) => {{
    currentStock = e.target.value;
    currentData = getData(currentStock);
    renderAll();
  }});
  
  // Time range
  document.querySelectorAll('.time-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      timeWindow = +btn.dataset.range;
      renderAll();
    }});
  }});
  
  // Sliders
  const bind = (id, valId, fn) => {{
    const el = document.getElementById(id);
    const vEl = document.getElementById(valId);
    let t;
    el.addEventListener('input', () => {{
      vEl.textContent = el.value;
      clearTimeout(t); t = setTimeout(renderAll, 150);
    }});
  }};
  bind('bollN', 'bollNVal', renderAll);
  bind('bollK', 'bollKVal', renderAll);
  bind('rsiN', 'rsiNVal', renderAll);
  bind('macdFast', 'macdFastVal', renderAll);
  bind('macdSlow', 'macdSlowVal', renderAll);
  bind('macdSig', 'macdSigVal', renderAll);
  
  window.addEventListener('resize', () => {{
    chartMain?.resize();
    chartRsi?.resize();
    chartMacd?.resize();
  }});
}});
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✓ 已生成: {OUTPUT}")
print(f"  文件大小: {OUTPUT.stat().st_size / 1024:.0f} KB")
