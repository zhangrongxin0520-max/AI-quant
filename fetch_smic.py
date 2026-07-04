#!/usr/bin/env python3
"""获取中芯国际近一年交易数据并存储为本地JSON/CSV"""
import urllib.request, json, csv, os, sys

TOKEN = 'ab925ba9052ea9025043db55278797a8e42bc62927cce807583d1a61'
API_URL = 'https://api.tushare.pro'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def call_tushare(api_name, params, fields=None):
    payload = {
        'api_name': api_name,
        'token': TOKEN,
        'params': params,
    }
    if fields:
        payload['fields'] = fields
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read().decode('utf-8'))

# 中芯国际 A股 688981.SH，时间范围近一年
ts_code = '688981.SH'
start_date = '20250704'
end_date = '20260704'

# 尝试多个接口
attempts = [
    ('daily', {'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
     'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'),
    ('bak_daily', {'ts_code': '688981', 'start_date': start_date, 'end_date': end_date},
     'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'),
    ('stk_weekly_monthly', {'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date, 'period': 'D'},
     'ts_code,trade_date,open,high,low,close,vol,amount'),
    ('weekly', {'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
     'ts_code,trade_date,open,high,low,close,vol,amount'),
]

result = None
used_api = None
for api_name, params, fields in attempts:
    print(f"尝试接口: {api_name} ...")
    try:
        resp = call_tushare(api_name, params, fields)
        if resp.get('code') == 0 and resp.get('data') and resp['data'].get('items'):
            result = resp['data']
            used_api = api_name
            print(f"  ✓ {api_name} 成功，获取到 {len(result['items'])} 条记录")
            break
        else:
            print(f"  ✗ {api_name} 失败: {resp.get('msg', 'unknown error')}")
    except Exception as e:
        print(f"  ✗ {api_name} 异常: {e}")

if not result:
    print("\n所有Tushare接口均无权限，尝试使用MCP工具接口...")
    sys.exit(1)

# 解析数据
fields_list = result['fields']
items = result['items']
records = [dict(zip(fields_list, item)) for item in items]
# 按日期升序排列
records.sort(key=lambda x: x['trade_date'])

print(f"\n使用接口: {used_api}")
print(f"数据范围: {records[0]['trade_date']} ~ {records[-1]['trade_date']}")
print(f"总记录数: {len(records)}")
print(f"字段: {fields_list}")

# 存储为 JSON
json_path = os.path.join(OUT_DIR, 'smic_daily.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
print(f"\n已保存 JSON: {json_path}")

# 存储为 CSV
csv_path = os.path.join(OUT_DIR, 'smic_daily.csv')
with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields_list)
    writer.writeheader()
    writer.writerows(records)
print(f"已保存 CSV: {csv_path}")

# 打印前5条和后5条
print("\n前5条记录:")
for r in records[:5]:
    print(f"  {r['trade_date']}  O:{r['open']}  H:{r['high']}  L:{r['low']}  C:{r['close']}  V:{r.get('vol','N/A')}")
print("后5条记录:")
for r in records[-5:]:
    print(f"  {r['trade_date']}  O:{r['open']}  H:{r['high']}  L:{r['low']}  C:{r['close']}  V:{r.get('vol','N/A')}")
